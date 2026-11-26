"""Server-side notification scheduling. Runs every 5 minutes (hooks.scheduler_events).

For every person with at least one active push subscription, in *their* timezone:
  * habit reminders   - at a habit's reminder time, if it's due today and not done yet;
  * daily reminder    - at the profile's daily time, if anything due today is still open;
  * challenge nudge   - at 19:00, if a running challenge's habit isn't done yet today;
  * weekly summary    - on the summary weekday (Atomic Streak Settings) at 18:00.
Badges and finished challenges are pushed straight after the check-in (push.send_milestone).

A notification fires in the 30 minutes after its time, so a late or skipped scheduler run still
delivers it, and an atomic Redis key makes sure each one goes out at most once.
"""

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import frappe
from frappe.utils import cint

from atomic_streak.constants import PARTICIPATION, PROFILE, SETTINGS, SUBSCRIPTION, ParticipationStatus
from atomic_streak.services import push
from atomic_streak.utils import get_user_timezone

WINDOW = timedelta(minutes=30)
CHALLENGE_TIME = time(19, 0)
WEEKLY_TIME = time(18, 0)
APP = "/atomic-streak"


def run(now: datetime | None = None) -> None:
	"""Scheduler entry point."""
	if not push.config()["enabled"]:
		return
	now = now or datetime.now(timezone.utc)
	users = frappe.get_all(SUBSCRIPTION, filters={"is_active": 1}, distinct=True, pluck="user")
	for user in users:
		try:
			process_user(user, now)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title=f"Atomic Streak reminders failed for {user}")


def _claim(user: str, key: str, day) -> bool:
	"""True the first time only (per user, key and local day). Atomic across workers."""
	name = frappe.cache.make_key(f"atomic_streak:sent:{user}:{key}:{day}")
	return bool(frappe.cache.set(name, 1, nx=True, ex=2 * 24 * 3600))


def _due(local: datetime, at: time | None) -> bool:
	if at is None:
		return False
	start = local.replace(hour=at.hour, minute=at.minute, second=0, microsecond=0)
	return start <= local < start + WINDOW


def _parse_hhmm(value) -> time | None:
	if not value:
		return None
	if isinstance(value, timedelta):  # MariaDB TIME comes back as a timedelta
		secs = int(value.total_seconds()) % 86400
		return time(secs // 3600, (secs % 3600) // 60)
	try:
		h, m = str(value).split(":")[:2]
		return time(int(h), int(m))
	except (ValueError, TypeError):
		return None


def process_user(user: str, now: datetime) -> list[str]:
	"""Send whatever is due for one user. Returns the keys that were sent (for tests/logs)."""
	from atomic_streak.services import habits

	profile = frappe.db.get_value(
		PROFILE,
		user,
		["daily_reminder_enabled", "daily_reminder_time", "weekly_summary_enabled", "current_streak"],
		as_dict=True,
	)
	if not profile:
		return []
	local = now.astimezone(ZoneInfo(get_user_timezone(user)))
	today = local.date()
	sent: list[str] = []

	view = None

	def today_view():
		nonlocal view
		if view is None:
			view = habits.today_view(user, today)
		return view

	def fire(key: str, title: str, body: str, url: str = APP, kind: str = "reminder") -> None:
		if _claim(user, key, today):
			push.send(user, title, body, url=url, tag=f"{key}-{today}", kind=kind)
			sent.append(key)

	# per-habit reminders: only a cheap query unless one is actually due now
	timed = frappe.get_all(
		"Atomic Habit",
		filters={"user": user, "status": "Active", "reminder_enabled": 1, "reminder_time": ["is", "set"]},
		fields=["name", "reminder_time"],
	)
	due_now = {h.name for h in timed if _due(local, _parse_hhmm(h.reminder_time))}
	if due_now:
		for h in today_view()["habits"]:
			if h["name"] in due_now and (h.get("completion") or {}).get("status") != "Completed":
				streak = cint(h.get("current_streak"))
				body = f"Keep your {streak}-day streak going." if streak > 1 else "A small step now counts."
				fire(f"habit-{h['name']}", f"Time for {h['habit_name']}", body, url=f"{APP}/")

	# daily reminder
	if profile.daily_reminder_enabled and _due(local, _parse_hhmm(profile.daily_reminder_time)):
		left = today_view()["summary"]["remaining"]
		if left:
			body = (
				f"Your {profile.current_streak}-day streak is waiting for today's check-in."
				if cint(profile.current_streak) > 1
				else "One small action is all it takes today."
			)
			fire("daily", f"{left} habit{'s' if left != 1 else ''} left today", body)

	# challenge nudge
	if _due(local, CHALLENGE_TIME):
		running = frappe.get_all(
			PARTICIPATION,
			filters={"user": user, "status": ParticipationStatus.ACTIVE},
			fields=["challenge", "habit", "start_date"],
		)
		if running:
			open_habits = {h["name"] for h in today_view()["habits"] if (h.get("completion") or {}).get("status") != "Completed"}
			behind = [p for p in running if p.habit in open_habits]
			if behind:
				p = behind[0]
				title, days = frappe.db.get_value("Atomic Challenge", p.challenge, ["title", "duration_days"]) or ("", 0)
				day_n = (today - p.start_date).days + 1
				fire(
					"challenge",
					f"Day {day_n} of {days}: {title}",
					"Today's check-in is still open. You've got this.",
					url=f"{APP}/challenges",
				)

	# weekly summary
	weekday = frappe.db.get_single_value(SETTINGS, "weekly_summary_day") or "Sunday"
	if profile.weekly_summary_enabled and local.strftime("%A") == weekday and _due(local, WEEKLY_TIME):
		from atomic_streak.services.coach import service as coach

		text = coach.weekly_summary(user)["text"]
		fire("weekly", "Your week in habits", text[:240], url=f"{APP}/insights", kind="summary")

	return sent
