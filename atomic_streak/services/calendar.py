"""Calendar views: day summaries for a range, and one day's habits in detail."""

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import flt, getdate

from atomic_streak.constants import CATEGORY, HABIT, HabitStatus
from atomic_streak.services import history
from atomic_streak.services.habits import get_owned
from atomic_streak.utils import user_today

MAX_RANGE_DAYS = 400  # a month view needs <= 42; a habit heatmap needs about a year
BACKFILL_DAYS = 7


def _range(user: str, start, end) -> tuple:
	today = user_today(user)
	try:
		start, end = getdate(start), getdate(end)
	except Exception:
		frappe.throw(_("Invalid dates."))
	if not start or not end or start > end:
		frappe.throw(_("Invalid date range."))
	if (end - start).days >= MAX_RANGE_DAYS:
		frappe.throw(_("Pick a shorter date range."))
	return start, end, today


def month_data(user: str, start, end, habit: str | None = None, cells: bool = False) -> dict:
	start, end, today = _range(user, start, end)
	if habit:
		get_owned(habit, user)
	if cells and (end - start).days > 41:
		frappe.throw(_("Per-habit detail is available for up to six weeks at a time."))
	hist = history.load(user, start, end, today, habit)
	out = {
		"start": str(start),
		"end": str(end),
		"today": str(today),
		"days": [hist.day_summary(d) for d in hist.days()],
		"habits": [{"name": h.name, "habit_name": h.habit_name, "icon": h.icon, "color": h.color} for h in hist.habits],
	}
	if cells:
		# per-habit states for the week grid; habits with nothing at all in range are left out
		grid = {h.name: [hist.state(h.name, d) for d in hist.days()] for h in hist.habits}
		out["cells"] = {name: states for name, states in grid.items() if any(s != history.OFF for s in states)}
	return out


def habit_history(user: str, habit: str, days: int = 119) -> dict:
	"""One habit's cells for its heatmap (default 17 weeks), with rates and comebacks."""
	get_owned(habit, user)
	today = user_today(user)
	days = max(7, min(int(days or 119), 371))
	start = today - timedelta(days=days - 1)
	hist = history.load(user, start, today, today, habit)
	week = history.rate(hist, habit, start=today - timedelta(days=6))
	month = history.rate(hist, habit, start=today - timedelta(days=29))
	return {
		"start": str(start),
		"today": str(today),
		"cells": [{"date": str(d), "state": hist.state(habit, d)} for d in hist.days()],
		"week_rate": week["rate"],
		"month_rate": month["rate"],
		"comebacks": history.comebacks(hist, habit),
	}


def day_detail(user: str, day) -> dict:
	today = user_today(user)
	day = getdate(day)
	if day > today:
		frappe.throw(_("You can't look ahead past today."))
	hist = history.load(user, day, day, today)
	cats = {c.name: c for c in frappe.get_all(CATEGORY, fields=["name", "category_name", "color"])}
	editable_day = day >= today - timedelta(days=BACKFILL_DAYS)
	items = []
	for h in hist.habits:
		state = hist.state(h.name, day)
		if state == history.OFF:
			continue
		c = hist.checkins.get((h.name, day))
		cat = cats.get(h.category) if h.category else None
		items.append(
			{
				"name": h.name,
				"habit_name": h.habit_name,
				"icon": h.icon,
				"color": h.color,
				"habit_type": h.habit_type,
				"daily_target": flt(h.daily_target),
				"target_unit": h.target_unit,
				"category": {"label": cat.category_name, "color": cat.color} if cat else None,
				"state": state,
				"value": flt(c.value) if c else 0,
				"target": flt(c.target) if c else flt(h.daily_target),
				"can_edit": editable_day and h.status == HabitStatus.ACTIVE,
			}
		)
	order = {history.MISSED: 0, history.PENDING: 1, history.PARTIAL: 2, history.DONE: 3, history.BONUS: 4}
	items.sort(key=lambda i: order.get(i["state"], 9))
	return {"date": str(day), "today": str(today), "summary": hist.day_summary(day), "habits": items}
