"""Calendar endpoints (signed-in app user, own data only)."""

import frappe

from atomic_streak.api.habit import _user
from atomic_streak.services import calendar


@frappe.whitelist(methods=["GET"])
def get_calendar_data(start: str, end: str, habit: str | None = None, cells: int = 0) -> dict:
	return calendar.month_data(_user(), start, end, habit or None, bool(frappe.utils.cint(cells)))


@frappe.whitelist(methods=["GET"])
def get_day(date: str) -> dict:
	return calendar.day_detail(_user(), date)


@frappe.whitelist(methods=["GET"])
def get_habit_history(habit: str, days: int = 119) -> dict:
	return calendar.habit_history(_user(), habit, days)
