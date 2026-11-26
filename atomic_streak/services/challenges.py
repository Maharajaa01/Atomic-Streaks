"""Challenges: join with a habit, track progress from real check-ins, finish with XP.

Rules
* A challenge runs for `duration_days` from the join date. Its target is the habit's scheduled
  days in that window.
* It is completed once the habit is done on at least 85% of those days (one slip a week is
  forgiven: 6 of 7, 18 of 21, 26 of 30). XP is granted then, once.
* It fails only when success is no longer reachable. Users can also leave (Abandoned).
* Progress is recomputed from the check-ins every time, so undoing check-ins can take a
  completed challenge (and its XP) back to active: rewards always match real history.
"""

import math
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import cint, getdate

from atomic_streak.constants import CHALLENGE, COMPLETION, HABIT, PARTICIPATION, CompletionStatus, HabitStatus, HabitType, ParticipationStatus
from atomic_streak.services import habits
from atomic_streak.services.streaks import load_schedule
from atomic_streak.utils import clean_text, user_today

SUCCESS_SHARE = 0.85
CUSTOM_XP_PER_DAY = 10
CUSTOM_XP_MAX = 300
MAX_CUSTOM = 30


def progress(p, today) -> dict:
	"""Pure-ish progress for a participation row (reads the habit's check-ins)."""
	sched = load_schedule(p.habit)
	start, end = getdate(p.start_date), getdate(p.end_date)
	days = list(sched.days(start, end))
	done_dates = {
		getdate(d)
		for d in frappe.get_all(
			COMPLETION,
			filters={"habit": p.habit, "status": CompletionStatus.COMPLETED, "completion_date": ["between", [start, end]]},
			pluck="completion_date",
		)
	}
	done = sum(1 for d in days if d in done_dates)
	target = len(days)
	needed = max(1, math.ceil(target * SUCCESS_SHARE)) if target else 0
	remaining = sum(1 for d in days if d > today or (d == today and d not in done_dates))
	return {"target": target, "needed": needed, "done": done, "remaining": remaining}


def recompute(name: str) -> bool:
	"""Re-derive one participation from its check-ins. True when it has just been completed."""
	p = frappe.get_doc(PARTICIPATION, name)
	if p.status == ParticipationStatus.ABANDONED:
		return False
	today = user_today(p.user)
	pr = progress(p, today)
	reward = cint(frappe.db.get_value(CHALLENGE, p.challenge, "xp_reward"))
	if pr["target"] and pr["done"] >= pr["needed"]:
		status, xp, completed_on = ParticipationStatus.COMPLETED, reward, p.completed_on or today
	elif pr["done"] + pr["remaining"] < pr["needed"] or (getdate(p.end_date) < today and pr["done"] < pr["needed"]):
		status, xp, completed_on = ParticipationStatus.FAILED, 0, None
	else:
		status, xp, completed_on = ParticipationStatus.ACTIVE, 0, None
	values = {"status": status, "days_completed": pr["done"], "xp_awarded": xp, "completed_on": completed_on}
	if status != ParticipationStatus.COMPLETED:
		values["celebrated"] = 0
	frappe.db.set_value(PARTICIPATION, name, values, update_modified=False)
	return status == ParticipationStatus.COMPLETED and p.status != ParticipationStatus.COMPLETED


def recompute_for(user: str, habit: str | None = None) -> list[str]:
	"""Recompute the user's challenges; returns the ones completed just now."""
	filters = {"user": user, "status": ["!=", ParticipationStatus.ABANDONED]}
	if habit:
		filters["habit"] = habit
	return [name for name in frappe.get_all(PARTICIPATION, filters=filters, pluck="name") if recompute(name)]


# ------------------------------------------------------------------ reads
def _visible(user: str) -> list:
	return frappe.get_all(
		CHALLENGE,
		filters={"is_active": 1},
		or_filters={"is_standard": 1, "created_by_user": user},
		fields=["name", "title", "description", "suggested_habit", "challenge_type", "duration_days", "xp_reward", "icon", "color", "is_standard", "created_by_user", "category"],
		order_by="is_standard desc, sort_order asc, creation asc",
	)


def overview(user: str) -> dict:
	today = user_today(user)
	challenges = _visible(user)
	by_name = {c.name: c for c in challenges}
	parts = frappe.get_all(
		PARTICIPATION,
		filters={"user": user},
		fields=["name", "challenge", "habit", "status", "start_date", "end_date", "days_completed", "completed_on", "xp_awarded"],
		order_by="creation desc",
	)
	habit_info = {
		h.name: h for h in frappe.get_all(HABIT, filters={"name": ["in", [p.habit for p in parts] or [""]]}, fields=["name", "habit_name", "icon", "color"])
	}
	mine = []
	for p in parts:
		c = by_name.get(p.challenge) or frappe.db.get_value(CHALLENGE, p.challenge, ["name", "title", "icon", "color", "duration_days", "xp_reward", "challenge_type"], as_dict=True)
		if not c:
			continue
		pr = progress(p, today) if p.status == ParticipationStatus.ACTIVE else {"target": None, "needed": None, "done": p.days_completed, "remaining": 0}
		day_n = min((today - getdate(p.start_date)).days + 1, cint(c.duration_days))
		mine.append(
			{
				**{k: (str(v) if k in ("start_date", "end_date", "completed_on") and v else v) for k, v in p.items()},
				"challenge_info": {k: c.get(k) for k in ("name", "title", "icon", "color", "duration_days", "xp_reward", "challenge_type")},
				"habit_info": habit_info.get(p.habit),
				"progress": pr,
				"day": max(day_n, 1),
			}
		)
	active_ids = {p.challenge for p in parts if p.status == ParticipationStatus.ACTIVE}
	return {
		"today": str(today),
		"mine": mine,
		"discover": [{**c, "joined": c.name in active_ids, "is_mine": c.created_by_user == user} for c in challenges],
	}


# ------------------------------------------------------------------ writes
def join(user: str, challenge: str, habit: str | None = None, habit_name: str | None = None) -> dict:
	c = frappe.db.get_value(CHALLENGE, challenge, ["name", "is_standard", "created_by_user", "is_active", "suggested_habit", "category", "icon", "color", "title"], as_dict=True)
	if not c or not (c.is_standard or c.created_by_user == user) or not c.is_active:
		frappe.throw(_("Challenge not found."), frappe.DoesNotExistError)
	if habit:
		doc = habits.get_owned(habit, user)
		if doc.habit_type == HabitType.ONE_TIME:
			frappe.throw(_("Pick a daily habit for a challenge, not a one-time goal."))
		if doc.status != HabitStatus.ACTIVE:
			frappe.throw(_("Resume this habit before using it in a challenge."))
	else:
		name = clean_text(habit_name or c.suggested_habit or c.title, _("Habit name"), 140, required=True)
		habit = habits.create(user, {"habit_name": name, "icon": c.icon, "color": c.color, "category": c.category, "start_date": str(user_today(user))})["name"]
	p = frappe.get_doc({"doctype": PARTICIPATION, "user": user, "challenge": challenge, "habit": habit, "start_date": user_today(user)})
	p.insert(ignore_permissions=True)
	recompute(p.name)
	return {"name": p.name, "habit": habit}


def leave(user: str, name: str) -> None:
	if frappe.db.get_value(PARTICIPATION, name, "user") != user:
		frappe.throw(_("Challenge not found."), frappe.DoesNotExistError)
	frappe.db.set_value(PARTICIPATION, name, {"status": ParticipationStatus.ABANDONED, "xp_awarded": 0})


def create_custom(user: str, title: str, duration_days: int, description: str | None = None, icon: str | None = None, color: str | None = None) -> dict:
	if frappe.db.count(CHALLENGE, {"created_by_user": user}) >= MAX_CUSTOM:
		frappe.throw(_("You can create up to {0} challenges.").format(MAX_CUSTOM))
	days = cint(duration_days)
	doc = frappe.get_doc(
		{
			"doctype": CHALLENGE,
			"title": title,
			"description": description,
			"challenge_type": "Custom",
			"duration_days": days,
			# reward is set by the server, never by the user: 10 XP a day, at most 300
			"xp_reward": min(max(days, 1) * CUSTOM_XP_PER_DAY, CUSTOM_XP_MAX),
			"icon": icon or "target",
			"color": color or "#FF9F43",
			"created_by_user": user,
			"is_standard": 0,
		}
	)
	doc.insert(ignore_permissions=True)
	return {"name": doc.name, "title": doc.title, "duration_days": doc.duration_days, "xp_reward": doc.xp_reward}
