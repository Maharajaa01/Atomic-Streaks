"""XP and levels.

XP is never stored as a running total that could drift or be gamed. It is always the sum of:
  * each Completed check-in's xp_awarded (by habit difficulty, fixed when the check-in is made;
    undoing a check-in removes its XP, partial check-ins earn none),
  * each earned achievement's xp_awarded (once per achievement, enforced by a unique index),
  * each completed challenge's xp_awarded.
Duplicate check-ins are impossible (unique habit+date), so XP can't be farmed.
"""

import math

import frappe
from frappe.utils import cint

from atomic_streak.constants import COMPLETION, PARTICIPATION, PROFILE, USER_ACHIEVEMENT, CompletionStatus

XP_BY_DIFFICULTY = {"Easy": 10, "Medium": 15, "Hard": 20}
ONE_TIME_XP = 30
LEVEL_STEP = 50  # reaching level L needs 50 * L * (L - 1) XP: 100, 300, 600, 1000, ...


def checkin_xp(status: str, difficulty: str | None, habit_type: str | None) -> int:
	if status != CompletionStatus.COMPLETED:
		return 0
	if habit_type == "One-time":
		return ONE_TIME_XP
	return XP_BY_DIFFICULTY.get(difficulty or "Medium", 15)


def level_for(xp: int) -> int:
	xp = max(cint(xp), 0)
	# largest L with 50 * L * (L - 1) <= xp
	return int((1 + math.sqrt(1 + 4 * xp / LEVEL_STEP)) // 2)


def xp_for_level(level: int) -> int:
	return LEVEL_STEP * level * (level - 1)


def level_progress(xp: int) -> dict:
	level = level_for(xp)
	start, nxt = xp_for_level(level), xp_for_level(level + 1)
	return {"xp": cint(xp), "level": level, "level_start": start, "next_level_at": nxt, "progress": round(100 * (xp - start) / (nxt - start))}


def total_xp(user: str) -> int:
	total = 0
	for doctype in (COMPLETION, USER_ACHIEVEMENT, PARTICIPATION):
		total += cint(frappe.db.sql(f"select coalesce(sum(xp_awarded), 0) from `tab{doctype}` where user = %s", user)[0][0])
	return total


def recompute(user: str) -> dict:
	xp = total_xp(user)
	level = level_for(xp)
	if frappe.db.exists(PROFILE, user):
		frappe.db.set_value(PROFILE, user, {"xp": xp, "level": level}, update_modified=False)
	return {"xp": xp, "level": level}
