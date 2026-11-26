"""Insights: completion rates, trends, best/most-missed habits, categories and a year heatmap.

Everything is computed from the same history grid as the calendar (services.history), so a
number on Insights always matches what the calendar shows.
"""

from collections import defaultdict
from datetime import timedelta

import frappe
from frappe.utils import cint

from atomic_streak.constants import CATEGORY, PROFILE, WEEKDAYS
from atomic_streak.services import history
from atomic_streak.utils import user_today

PERIODS = (7, 30, 90)
HEATMAP_DAYS = 365
MIN_DAYS_FOR_RANKING = 3


def dashboard(user: str, days: int = 30) -> dict:
	days = cint(days) if cint(days) in PERIODS else 30
	today = user_today(user)
	start = today - timedelta(days=days - 1)
	prev_start = start - timedelta(days=days)
	year_start = today - timedelta(days=HEATMAP_DAYS - 1)

	# one load covers the heatmap year and both comparison windows
	hist = history.load(user, min(year_start, prev_start), today, today)
	current = history.rate(hist, start=start)
	previous = history.rate(hist, start=prev_start, end=start - timedelta(days=1))

	trend, weekday_hits, weekday_sched = [], defaultdict(int), defaultdict(int)
	day = start
	while day <= today:
		r = history.rate(hist, start=day, end=day)
		trend.append({"date": str(day), "rate": r["rate"], "completed": r["completed"], "scheduled": r["scheduled"]})
		weekday_hits[day.weekday()] += r["completed"]
		weekday_sched[day.weekday()] += r["scheduled"]
		day += timedelta(days=1)

	cats = {c.name: c for c in frappe.get_all(CATEGORY, fields=["name", "category_name", "color"])}
	per_habit, per_cat = [], defaultdict(lambda: {"completed": 0, "scheduled": 0})
	for h in hist.habits:
		if h.habit_type == "One-time":
			continue
		r = history.rate(hist, h.name, start=start)
		missed = sum(1 for d in _days(start, today) if hist.state(h.name, d) == history.MISSED)
		per_habit.append(
			{
				"name": h.name,
				"habit_name": h.habit_name,
				"icon": h.icon,
				"color": h.color,
				"status": h.status,
				"completed": r["completed"],
				"scheduled": r["scheduled"],
				"rate": r["rate"],
				"missed": missed,
				"current_streak": cint(h.current_streak),
				"longest_streak": cint(h.longest_streak),
			}
		)
		key = h.category if h.category in cats else None
		per_cat[key]["completed"] += r["completed"]
		per_cat[key]["scheduled"] += r["scheduled"]

	ranked = [h for h in per_habit if h["scheduled"] >= MIN_DAYS_FOR_RANKING]
	best = sorted(ranked, key=lambda h: (-(h["rate"] or 0), -h["completed"]))[:5]
	struggling = sorted([h for h in ranked if h["missed"]], key=lambda h: (-h["missed"], h["rate"] or 0))[:5]

	categories = sorted(
		(
			{
				"category": key,
				"label": cats[key].category_name if key else "No category",
				"color": cats[key].color if key else "#9AA1B5",
				"completed": v["completed"],
				"scheduled": v["scheduled"],
				"rate": round(100 * v["completed"] / v["scheduled"]) if v["scheduled"] else None,
			}
			for key, v in per_cat.items()
			if v["scheduled"]
		),
		key=lambda c: -(c["rate"] or 0),
	)

	heat = []
	for d in _days(year_start, today):
		s = hist.day_summary(d)
		heat.append({"date": s["date"], "completed": s["completed"], "scheduled": s["scheduled"], "percent": s["percent"] if s["scheduled"] else None})

	profile = frappe.db.get_value(PROFILE, user, ["current_streak", "longest_streak", "total_completions"], as_dict=True) or {}
	window = history.History(start=start, end=today, today=today, habits=hist.habits, schedules=hist.schedules, checkins=hist.checkins)
	return {
		"days": days,
		"start": str(start),
		"today": str(today),
		"rate": current["rate"],
		"previous_rate": previous["rate"],
		"completed": current["completed"],
		"scheduled": current["scheduled"],
		"week_rate": history.rate(hist, start=today - timedelta(days=6))["rate"],
		"month_rate": history.rate(hist, start=today - timedelta(days=29))["rate"],
		"comebacks": history.comebacks(window),
		"streak": {
			"current": cint(profile.get("current_streak")),
			"longest": cint(profile.get("longest_streak")),
			"total_completions": cint(profile.get("total_completions")),
		},
		"trend": trend,
		"weekdays": [
			{
				"weekday": WEEKDAYS[i][:3],
				"rate": round(100 * weekday_hits[i] / weekday_sched[i]) if weekday_sched[i] else None,
				"scheduled": weekday_sched[i],
			}
			for i in range(7)
		],
		"habits": per_habit,
		"best": best,
		"struggling": struggling,
		"longest_streaks": sorted(per_habit, key=lambda h: -h["longest_streak"])[:5],
		"categories": categories,
		"heatmap": heat,
	}


def _days(start, end):
	day = start
	while day <= end:
		yield day
		day += timedelta(days=1)
