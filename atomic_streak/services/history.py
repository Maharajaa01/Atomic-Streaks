"""A user's check-in history as a grid of (habit x day) states.

Shared by the calendar, the per-habit heatmap and Insights so they always agree.

Cell states for a habit on a day:
  done     scheduled, and a Completed check-in exists
  partial  scheduled, check-in below target
  missed   scheduled, in the past, no check-in at all
  pending  scheduled today, not done yet (never counted as missed)
  bonus    not scheduled, but checked in anyway (shown, never counted in rates)
  off      not scheduled (includes paused/archived periods)

One-time goals are not part of rates or "missed" (they are due until done, so every earlier
day would otherwise look missed); their completion shows as a bonus cell on its day.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

import frappe
from frappe.utils import getdate

from atomic_streak.constants import COMPLETION, HABIT, CompletionStatus, HabitType
from atomic_streak.services.habits import schedules_for
from atomic_streak.services.schedule import Schedule

DONE, PARTIAL, MISSED, PENDING, BONUS, OFF = "done", "partial", "missed", "pending", "bonus", "off"
HABIT_FIELDS = [
	"name", "habit_name", "icon", "color", "category", "habit_type", "frequency", "interval_days",
	"start_date", "end_date", "status", "current_streak", "longest_streak", "daily_target", "target_unit",
]


@dataclass
class History:
	start: date
	end: date
	today: date
	habits: list = field(default_factory=list)
	schedules: dict[str, Schedule] = field(default_factory=dict)
	checkins: dict[tuple[str, date], dict] = field(default_factory=dict)

	def state(self, habit: str, day: date) -> str:
		c = self.checkins.get((habit, day))
		schedule = self.schedules[habit]
		if schedule.habit_type == HabitType.ONE_TIME or not schedule.is_scheduled(day):
			return BONUS if c else OFF
		if c:
			return DONE if c["status"] == CompletionStatus.COMPLETED else PARTIAL
		if day > self.today:
			return OFF
		return PENDING if day == self.today else MISSED

	def days(self):
		day = self.start
		while day <= self.end:
			yield day
			day += timedelta(days=1)

	def day_summary(self, day: date) -> dict:
		counts = defaultdict(int)
		for h in self.habits:
			counts[self.state(h.name, day)] += 1
		scheduled = counts[DONE] + counts[PARTIAL] + counts[MISSED] + counts[PENDING]
		if day > self.today:
			kind = "future"
		elif not scheduled:
			kind = "bonus" if counts[BONUS] else "none"
		elif counts[DONE] == scheduled:
			kind = "done"
		elif counts[DONE] or counts[PARTIAL]:
			kind = "partial"
		elif day == self.today:
			kind = "pending"
		else:
			kind = "missed"
		return {
			"date": str(day),
			"scheduled": scheduled,
			"completed": counts[DONE],
			"partial": counts[PARTIAL],
			"missed": counts[MISSED],
			"pending": counts[PENDING],
			"bonus": counts[BONUS],
			"percent": round(100 * counts[DONE] / scheduled) if scheduled else 0,
			"state": kind,
		}


def load(user: str, start: date, end: date, today: date, habit: str | None = None) -> History:
	filters = {"user": user}
	if habit:
		filters["name"] = habit
	rows = frappe.get_all(HABIT, filters=filters, fields=HABIT_FIELDS, order_by="sort_order asc, creation asc")
	hist = History(start=start, end=end, today=today, habits=rows, schedules=schedules_for(rows))
	if rows:
		for c in frappe.get_all(
			COMPLETION,
			filters={
				"user": user,
				"habit": ["in", [r.name for r in rows]],
				"completion_date": ["between", [start, end]],
			},
			fields=["name", "habit", "completion_date", "value", "target", "status"],
		):
			hist.checkins[(c.habit, getdate(c.completion_date))] = c
	return hist


def rate(hist: History, habit: str | None = None, start: date | None = None, end: date | None = None) -> dict:
	"""Completion rate over scheduled days. Today only counts once it is done (pending isn't a miss)."""
	start, end = start or hist.start, min(end or hist.end, hist.today)
	names = [habit] if habit else [h.name for h in hist.habits]
	done = scheduled = 0
	day = start
	while day <= end:
		for n in names:
			s = hist.state(n, day)
			if s == DONE:
				done += 1
				scheduled += 1
			elif s in (PARTIAL, MISSED):
				scheduled += 1
		day += timedelta(days=1)
	return {"completed": done, "scheduled": scheduled, "rate": round(100 * done / scheduled) if scheduled else None}


def comebacks(hist: History, habit: str | None = None) -> int:
	"""Times a habit was done on the scheduled day right after a missed one: bouncing back."""
	count = 0
	for h in hist.habits if not habit else [x for x in hist.habits if x.name == habit]:
		last = None
		for day in hist.days():
			s = hist.state(h.name, day)
			if s in (DONE, PARTIAL, MISSED):
				if s == DONE and last == MISSED:
					count += 1
				last = s
	return count
