"""When is a habit due? Pure functions, no database access (easy to test).

A habit is *scheduled* on a day when the day is inside [start_date, end_date] and matches its
frequency:

* Daily          every day
* Specific Days  the chosen weekdays
* Every N Days   start_date, start_date + N, start_date + 2N, ...

One-time goals are "due" every day from the start until they are done (or the end date); they
have no streak.

Days inside a pause period (the habit was Paused or Archived) are not scheduled: they neither
count towards a streak nor break it, exactly like a day the habit isn't planned for.
"""

from collections.abc import Iterable, Iterator
from datetime import date, timedelta

from frappe.utils import getdate

from atomic_streak.constants import WEEKDAYS, Frequency, HabitType


class Schedule:
	"""A habit's schedule, prepared once so checking many days is cheap."""

	__slots__ = ("end", "frequency", "habit_type", "interval", "pauses", "start", "weekdays")

	def __init__(self, habit, weekdays: Iterable[str] | None = None, pauses: Iterable | None = None):
		get = habit.get if hasattr(habit, "get") else lambda k, d=None: getattr(habit, k, d)
		self.frequency = get("frequency") or Frequency.DAILY
		self.habit_type = get("habit_type") or HabitType.BUILD
		self.start = getdate(get("start_date"))
		end = get("end_date")
		self.end = getdate(end) if end else None
		self.interval = max(int(get("interval_days") or 1), 1)
		if weekdays is None:
			weekdays = [row.get("weekday") if hasattr(row, "get") else row.weekday for row in (get("schedule") or [])]
		self.weekdays = frozenset(WEEKDAYS.index(d) for d in weekdays if d in WEEKDAYS)
		if pauses is None:
			pauses = get("pauses") or []
		self.pauses = tuple(
			(getdate(_pget(p, "from_date")), getdate(_pget(p, "to_date")) if _pget(p, "to_date") else None)
			for p in pauses
			if _pget(p, "from_date")
		)

	def is_paused(self, day: date) -> bool:
		return any(start <= day and (end is None or day <= end) for start, end in self.pauses)

	def is_scheduled(self, day: date) -> bool:
		if day < self.start or (self.end and day > self.end):
			return False
		if self.pauses and self.is_paused(day):
			return False
		if self.frequency == Frequency.SPECIFIC_DAYS:
			return day.weekday() in self.weekdays
		if self.frequency == Frequency.EVERY_N_DAYS:
			return (day - self.start).days % self.interval == 0
		return True

	def days(self, start: date, end: date) -> Iterator[date]:
		"""Scheduled days in [start, end], oldest first."""
		day = max(start, self.start)
		last = min(end, self.end) if self.end else end
		while day <= last:
			if self.is_scheduled(day):
				yield day
			day += timedelta(days=1)

	def days_back(self, end: date) -> Iterator[date]:
		"""Scheduled days from `end` back to the start date, newest first."""
		day = min(end, self.end) if self.end else end
		while day >= self.start:
			if self.is_scheduled(day):
				yield day
			day -= timedelta(days=1)


def _pget(row, key):
	if isinstance(row, (tuple, list)):
		return row[0] if key == "from_date" else (row[1] if len(row) > 1 else None)
	return row.get(key) if hasattr(row, "get") else getattr(row, key, None)
