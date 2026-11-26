"""Pure streak-engine tests (no database).

Run:  CI=1 bench --site <site> run-tests --module atomic_streak.tests.test_streaks
"""

import unittest
from datetime import date, timedelta

from atomic_streak.services.schedule import Schedule
from atomic_streak.services.streaks import habit_stats, overall_stats

TODAY = date(2026, 11, 20)  # a Friday


def d(n: int) -> date:
	"""n days before TODAY."""
	return TODAY - timedelta(days=n)


def sched(frequency="Daily", start=d(60), end=None, weekdays=(), interval=1, habit_type="Build"):
	return Schedule(
		{"frequency": frequency, "start_date": start, "end_date": end, "interval_days": interval, "habit_type": habit_type},
		list(weekdays),
	)


class TestSchedule(unittest.TestCase):
	def test_daily_respects_start_and_end(self):
		s = sched(start=d(3), end=d(1))
		self.assertEqual([x for x in (d(4), d(3), d(1), d(0)) if s.is_scheduled(x)], [d(3), d(1)])

	def test_specific_days(self):
		s = sched("Specific Days", weekdays=["Monday", "Friday"])
		self.assertTrue(s.is_scheduled(TODAY))  # Friday
		self.assertTrue(s.is_scheduled(d(4)))  # Monday
		self.assertFalse(s.is_scheduled(d(1)))  # Thursday

	def test_every_n_days_anchored_on_start(self):
		s = sched("Every N Days", start=d(9), interval=3)
		self.assertEqual(list(s.days(d(9), TODAY)), [d(9), d(6), d(3), d(0)])


class TestHabitStreak(unittest.TestCase):
	def test_counts_today(self):
		self.assertEqual(habit_stats(sched(), {d(0), d(1), d(2)}, TODAY).current_streak, 3)

	def test_today_pending_is_grace(self):
		self.assertEqual(habit_stats(sched(), {d(1), d(2)}, TODAY).current_streak, 2)

	def test_missed_day_breaks_and_longest_survives(self):
		stats = habit_stats(sched(), {d(5), d(4), d(3), d(1)}, TODAY)
		self.assertEqual((stats.current_streak, stats.longest_streak), (1, 3))

	def test_missed_yesterday_today_pending(self):
		self.assertEqual(habit_stats(sched(), {d(3), d(2)}, TODAY).current_streak, 0)

	def test_unscheduled_days_do_not_break(self):
		# Mon/Wed/Fri habit done on Mon d(4), Wed d(2), Fri today: 3 in a row
		s = sched("Specific Days", weekdays=["Monday", "Wednesday", "Friday"])
		self.assertEqual(habit_stats(s, {d(4), d(2), d(0)}, TODAY).current_streak, 3)
		# missing Wednesday breaks it
		self.assertEqual(habit_stats(s, {d(4), d(0)}, TODAY).current_streak, 1)

	def test_bonus_completion_on_unscheduled_day_does_not_inflate(self):
		s = sched("Specific Days", weekdays=["Friday"])
		stats = habit_stats(s, {d(0), d(1), d(2), d(7)}, TODAY)  # d(1), d(2) aren't Fridays
		self.assertEqual(stats.current_streak, 2)
		self.assertEqual(stats.total_completions, 4)

	def test_every_n_days(self):
		s = sched("Every N Days", start=d(9), interval=3)
		self.assertEqual(habit_stats(s, {d(9), d(6), d(3)}, TODAY).current_streak, 3)  # today pending
		self.assertEqual(habit_stats(s, {d(9), d(3)}, TODAY).current_streak, 1)

	def test_ended_habit_keeps_final_streak(self):
		s = sched(start=d(10), end=d(5))
		self.assertEqual(habit_stats(s, {d(7), d(6), d(5)}, TODAY).current_streak, 3)

	def test_future_start_and_empty(self):
		self.assertEqual(habit_stats(sched(start=TODAY + timedelta(days=2)), set(), TODAY).current_streak, 0)
		stats = habit_stats(sched(), set(), TODAY)
		self.assertEqual((stats.current_streak, stats.longest_streak, stats.total_completions), (0, 0, 0))

	def test_one_time_goal_has_no_streak(self):
		stats = habit_stats(sched(habit_type="One-time"), {d(0)}, TODAY)
		self.assertEqual((stats.current_streak, stats.total_completions), (0, 1))

	def test_longest_over_long_history(self):
		done = {d(i) for i in range(40, 70)} | {d(i) for i in range(0, 5)}
		stats = habit_stats(sched(start=d(100)), done, TODAY)
		self.assertEqual((stats.current_streak, stats.longest_streak), (5, 30))


class TestOverallStreak(unittest.TestCase):
	def test_any_scheduled_habit_done_counts(self):
		a = (sched(), {d(1), d(3)})
		b = (sched(), {d(2)})
		self.assertEqual(overall_stats([a, b], TODAY), (3, 3))  # today pending

	def test_days_with_nothing_scheduled_are_skipped(self):
		fri = (sched("Specific Days", weekdays=["Friday"]), {d(7), d(14), d(0)})
		self.assertEqual(overall_stats([fri], TODAY)[0], 3)

	def test_gap_breaks(self):
		a = (sched(start=d(5)), {d(5), d(4), d(1)})
		self.assertEqual(overall_stats([a], TODAY), (1, 2))

	def test_no_habits(self):
		self.assertEqual(overall_stats([], TODAY), (0, 0))


class TestPauses(unittest.TestCase):
	def test_paused_days_neither_count_nor_break(self):
		# paused d(4)..d(2): done d(6), d(5), then resumed and done d(1), today pending
		s = Schedule(
			{"frequency": "Daily", "start_date": d(30), "habit_type": "Build"}, [], [(d(4), d(2))]
		)
		self.assertFalse(s.is_scheduled(d(3)))
		stats = habit_stats(s, {d(6), d(5), d(1)}, TODAY)
		self.assertEqual(stats.current_streak, 3)

	def test_open_pause_covers_today(self):
		s = Schedule({"frequency": "Daily", "start_date": d(30)}, [], [{"from_date": d(1), "to_date": None}])
		self.assertFalse(s.is_scheduled(TODAY))
		self.assertTrue(s.is_scheduled(d(2)))
