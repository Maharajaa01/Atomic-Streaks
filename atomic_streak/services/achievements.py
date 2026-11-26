"""Achievements: checked after every check-in change, earned once, never revoked.

Each criterion reads real, recalculated data (streaks, totals, weekly rate), so an achievement
can only be earned by doing the habits. A unique index on (user, achievement) makes earning
the same badge twice impossible.
"""

from datetime import timedelta

import frappe
from frappe.utils import cint

from atomic_streak.constants import ACHIEVEMENT, HABIT, PARTICIPATION, PROFILE, USER_ACHIEVEMENT, ParticipationStatus
from atomic_streak.utils import user_today

MIN_SCHEDULED_FOR_CONSISTENCY = 5


def _metrics(user: str) -> dict:
	from atomic_streak.services import history

	p = frappe.db.get_value(PROFILE, user, ["total_completions"], as_dict=True) or {}
	longest = cint(frappe.db.sql(f"select coalesce(max(longest_streak), 0) from `tab{HABIT}` where user = %s", user)[0][0])
	today = user_today(user)
	# last full week (yesterday and the six days before): today is still in progress
	start, end = today - timedelta(days=7), today - timedelta(days=1)
	hist = history.load(user, start, end, today)
	week = history.rate(hist, start=start, end=end)
	return {
		"First Completion": cint(p.get("total_completions")),
		"Total Completions": cint(p.get("total_completions")),
		"Streak": longest,
		"Weekly Consistency": (week["rate"] or 0) if week["scheduled"] >= MIN_SCHEDULED_FOR_CONSISTENCY else 0,
		"Challenge Completed": frappe.db.count(PARTICIPATION, {"user": user, "status": ParticipationStatus.COMPLETED}),
		"Habits Created": frappe.db.count(HABIT, {"user": user}),
	}


def evaluate(user: str) -> list[str]:
	"""Award every achievement the user now qualifies for. Returns the newly earned codes."""
	earned = set(frappe.get_all(USER_ACHIEVEMENT, filters={"user": user}, pluck="achievement"))
	candidates = [
		a
		for a in frappe.get_all(ACHIEVEMENT, filters={"is_active": 1}, fields=["name", "criteria", "threshold", "xp_reward"])
		if a.name not in earned
	]
	if not candidates:
		return []
	metrics = _metrics(user)
	new = []
	for a in candidates:
		if metrics.get(a.criteria, 0) >= (a.threshold or 0):
			doc = frappe.get_doc(
				{"doctype": USER_ACHIEVEMENT, "user": user, "achievement": a.name, "xp_awarded": cint(a.xp_reward)}
			)
			doc.flags.ignore_owner_check = True  # awarded by the server, possibly during another user's admin action
			try:
				doc.insert(ignore_permissions=True)
				new.append(a.name)
			except (frappe.UniqueValidationError, frappe.DuplicateEntryError):
				frappe.clear_messages()  # earned by a parallel request
	return new


def list_for(user: str) -> list[dict]:
	earned = {
		r.achievement: r
		for r in frappe.get_all(USER_ACHIEVEMENT, filters={"user": user}, fields=["name", "achievement", "achieved_on", "seen"])
	}
	out = []
	for a in frappe.get_all(
		ACHIEVEMENT,
		filters={"is_active": 1},
		fields=["name", "title", "description", "icon", "color", "criteria", "threshold", "xp_reward"],
		order_by="sort_order asc",
	):
		e = earned.get(a.name)
		out.append({**a, "earned": bool(e), "achieved_on": str(e.achieved_on) if e else None})
	return out


def unseen(user: str) -> list[dict]:
	rows = frappe.get_all(USER_ACHIEVEMENT, filters={"user": user, "seen": 0}, fields=["name", "achievement", "xp_awarded"], order_by="creation asc")
	if not rows:
		return []
	meta = {a.name: a for a in frappe.get_all(ACHIEVEMENT, filters={"name": ["in", [r.achievement for r in rows]]}, fields=["name", "title", "description", "icon", "color"])}
	return [
		{"name": r.name, "code": r.achievement, "xp": r.xp_awarded, **{k: meta[r.achievement][k] for k in ("title", "description", "icon", "color")}}
		for r in rows
		if r.achievement in meta
	]


def mark_seen(user: str, names: list[str]) -> None:
	for name in names or []:
		if frappe.db.get_value(USER_ACHIEVEMENT, name, "user") == user:
			frappe.db.set_value(USER_ACHIEVEMENT, name, "seen", 1, update_modified=False)


