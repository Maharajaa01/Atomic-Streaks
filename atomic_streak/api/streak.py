"""Streak summary (signed-in app user, own data only)."""

import frappe
from frappe.utils import cint

from atomic_streak.api.habit import _user
from atomic_streak.constants import HABIT, PROFILE, HabitStatus


@frappe.whitelist(methods=["GET"])
def get_streak_summary() -> dict:
	user = _user()
	p = frappe.db.get_value(PROFILE, user, ["current_streak", "longest_streak", "total_completions"], as_dict=True) or {}
	habits = frappe.get_all(
		HABIT,
		filters={"user": user, "status": ["!=", HabitStatus.ARCHIVED]},
		fields=["name", "habit_name", "icon", "color", "current_streak", "longest_streak", "total_completions"],
		order_by="current_streak desc, longest_streak desc",
	)
	return {
		"current": cint(p.get("current_streak")),
		"longest": cint(p.get("longest_streak")),
		"total_completions": cint(p.get("total_completions")),
		"habits": habits,
	}
