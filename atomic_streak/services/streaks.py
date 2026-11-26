"""The streak engine.

Rules (product spec §8):
* Streaks count **scheduled** days only. Unscheduled days never break a streak and never add to it.
* A scheduled day counts when it has a *Completed* check-in (value reached the target). A
  partial check-in does not count, and doesn't break anything on its own: the day is just not done.
* Today is a grace day: if today is scheduled but not done yet, the streak is still alive.
* Nothing is stored incrementally. Every change to a check-in recomputes the habit's numbers
  from its full history while the habit row is locked, so editing or deleting an old check-in
  can never leave an inflated streak behind, and two simultaneous check-ins can't race.

The overall (profile) streak counts days on which the user completed at least one habit that
was scheduled that day, skipping days with nothing scheduled, with the same grace for today.
"""

from dataclasses import dataclass
from datetime import date, timedelta

import frappe
from frappe.utils import getdate, now_datetime

from atomic_streak.constants import COMPLETION, HABIT, PROFILE, CompletionStatus, HabitType
from atomic_streak.services.schedule import Schedule
from atomic_streak.utils import user_today


@dataclass
class HabitStats:
	current_streak: int = 0
	longest_streak: int = 0
	total_completions: int = 0
	last_completed_on: date | None = None


def habit_stats(schedule: Schedule, done: set[date], today: date) -> HabitStats:
	"""Streak numbers for one habit. `done` = dates with a Completed check-in."""
	stats = HabitStats(total_completions=len(done), last_completed_on=max(done) if done else None)
	if schedule.habit_type == HabitType.ONE_TIME:
		return stats  # a one-time goal has no streak

	# current: walk back over scheduled days; today may still be pending
	for day in schedule.days_back(today):
		if day in done:
			stats.current_streak += 1
		elif day == today:
			continue
		else:
			break

	# longest: one pass forward over the whole history
	run = 0
	for day in schedule.days(schedule.start, today):
		if day in done:
			run += 1
			stats.longest_streak = max(stats.longest_streak, run)
		elif day != today:
			run = 0
	stats.longest_streak = max(stats.longest_streak, stats.current_streak)
	return stats


def overall_stats(schedules: list[tuple[Schedule, set[date]]], today: date) -> tuple[int, int]:
	"""(current, longest) "show-up" streak across all habits."""
	starts = [s.start for s, _ in schedules if s.habit_type != HabitType.ONE_TIME]
	if not starts:
		return 0, 0

	day, first = today, min(starts)
	results: list[bool | None] = []  # newest first; None = nothing scheduled that day
	while day >= first:
		due = [done for s, done in schedules if s.habit_type != HabitType.ONE_TIME and s.is_scheduled(day)]
		results.append(None if not due else any(day in done for done in due))
		day -= timedelta(days=1)

	current = 0
	for i, hit in enumerate(results):
		if hit is None:
			continue
		if hit:
			current += 1
		elif i == 0:
			continue  # today, still pending
		else:
			break

	longest = run = 0
	for i, hit in enumerate(reversed(results)):
		if hit is None:
			continue
		if hit:
			run += 1
			longest = max(longest, run)
		elif i != len(results) - 1:
			run = 0
	return current, max(longest, current)


# ------------------------------------------------------------------ database side
def completed_dates(habit: str) -> set[date]:
	return {
		getdate(d)
		for d in frappe.get_all(
			COMPLETION, filters={"habit": habit, "status": CompletionStatus.COMPLETED}, pluck="completion_date"
		)
	}


def load_schedule(habit: str) -> Schedule:
	doc = frappe.db.get_value(
		HABIT, habit, ["frequency", "habit_type", "start_date", "end_date", "interval_days"], as_dict=True
	)
	weekdays = frappe.get_all(
		"Atomic Habit Schedule", filters={"parent": habit, "parenttype": HABIT}, pluck="weekday"
	)
	pauses = frappe.get_all(
		"Atomic Habit Pause", filters={"parent": habit, "parenttype": HABIT}, fields=["from_date", "to_date"]
	)
	return Schedule(doc, weekdays, pauses)


def recompute_habit(habit: str, user: str | None = None) -> HabitStats | None:
	"""Recalculate and store one habit's numbers (row-locked)."""
	if not frappe.db.sql(f"select name from `tab{HABIT}` where name = %s for update", habit):
		return None
	user = user or frappe.db.get_value(HABIT, habit, "user")
	stats = habit_stats(load_schedule(habit), completed_dates(habit), user_today(user))
	frappe.db.set_value(
		HABIT,
		habit,
		{
			"current_streak": stats.current_streak,
			"longest_streak": stats.longest_streak,
			"total_completions": stats.total_completions,
			"last_completed_on": stats.last_completed_on,
		},
		update_modified=False,
	)
	return stats


def recompute_profile(user: str) -> dict | None:
	"""Recalculate the user's overall streak and totals (row-locked)."""
	if not frappe.db.sql(f"select name from `tab{PROFILE}` where name = %s for update", user):
		return None
	habits = frappe.get_all(HABIT, filters={"user": user}, pluck="name")
	done_by_habit: dict[str, set[date]] = {h: set() for h in habits}
	for row in frappe.get_all(
		COMPLETION,
		filters={"user": user, "status": CompletionStatus.COMPLETED},
		fields=["habit", "completion_date"],
	):
		done_by_habit.setdefault(row.habit, set()).add(getdate(row.completion_date))
	schedules = [(load_schedule(h), done_by_habit[h]) for h in habits]
	current, longest = overall_stats(schedules, user_today(user))
	values = {
		"current_streak": current,
		"longest_streak": longest,
		"total_completions": sum(len(d) for d in done_by_habit.values()),
		"stats_updated_at": now_datetime(),
	}
	frappe.db.set_value(PROFILE, user, values, update_modified=False)
	return values


def refresh(habit: str | None, user: str) -> None:
	"""After any check-in or schedule change: streaks first, then everything that reads them."""
	from atomic_streak.services import gamification

	if habit:
		recompute_habit(habit, user)
	recompute_profile(user)
	gamification.refresh(user, habit)
