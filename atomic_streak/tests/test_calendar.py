"""History, calendar, pause tracking and Insights against a hand-checkable history.

Run:  CI=1 bench --site <site> run-tests --module atomic_streak.tests.test_calendar
"""

from datetime import timedelta

import frappe
from frappe.tests.utils import FrappeTestCase

from atomic_streak.constants import COMPLETION
from atomic_streak.services import accounts, analytics, calendar, habits
from atomic_streak.utils import user_today

DOMAIN = "atomicstreak.test"


class TestCalendarAndInsights(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.db.set_single_value("Atomic Streak Settings", "allow_signup", 1)
		cls.user = accounts.create_account("Cal Tester", f"cal@{DOMAIN}", "Lantern-Orbit-93!", "Asia/Kolkata")
		cls.other = accounts.create_account("Cal Other", f"cal2@{DOMAIN}", "Lantern-Orbit-93!", "Asia/Kolkata")
		frappe.set_user(cls.user)
		cls.today = t = user_today(cls.user)
		start = str(t - timedelta(days=6))
		# A: daily, done d6 d5 d4, missed d3, done d2 d1, today pending -> 5/6 of past days
		cls.a = habits.create(cls.user, {"habit_name": "A daily", "start_date": start, "category": "Health"})["name"]
		# B: target 4; partial on d1, done today
		cls.b = habits.create(cls.user, {"habit_name": "B count", "start_date": start, "daily_target": 4, "category": "Reading"})["name"]
		# C: one-time goal finished d2
		cls.c = habits.create(cls.user, {"habit_name": "C goal", "start_date": start, "habit_type": "One-time"})["name"]
		for n in (6, 5, 4, 2, 1):
			cls.checkin(cls.a, n)
		cls.checkin(cls.b, 1, value=2)
		cls.checkin(cls.b, 0, value=4)
		cls.checkin(cls.c, 2)

	@classmethod
	def checkin(cls, habit, days_ago, value=None):
		# bypass the 7-day window rule only where needed; all of these are inside it
		habits.check_in(cls.user, habit, cls.today - timedelta(days=days_ago), value)

	def setUp(self):
		frappe.set_user(self.user)

	def tearDown(self):
		frappe.set_user("Administrator")

	def d(self, n):
		return str(self.today - timedelta(days=n))

	def test_month_data_day_states(self):
		data = calendar.month_data(self.user, self.d(6), str(self.today + timedelta(days=2)))
		by = {x["date"]: x for x in data["days"]}
		self.assertEqual(by[self.d(3)]["state"], "missed")  # A and B both missed, nothing done
		self.assertEqual(by[self.d(3)]["missed"], 2)
		self.assertEqual(by[self.d(1)]["state"], "partial")  # A done, B partial
		self.assertEqual((by[self.d(1)]["completed"], by[self.d(1)]["partial"]), (1, 1))
		self.assertEqual(by[str(self.today)]["state"], "partial")  # B done, A pending
		self.assertEqual(by[str(self.today)]["pending"], 1)
		self.assertEqual(by[str(self.today + timedelta(days=1))]["state"], "future")
		self.assertEqual(by[self.d(2)]["bonus"], 1)  # the one-time goal never counts as scheduled
		self.assertEqual({h["name"] for h in data["habits"]}, {self.a, self.b, self.c})

	def test_week_cells(self):
		data = calendar.month_data(self.user, self.d(6), str(self.today), cells=True)
		self.assertEqual(data["cells"][self.a], ["done", "done", "done", "missed", "done", "done", "pending"])
		self.assertEqual(data["cells"][self.c][4], "bonus")
		with self.assertRaises(frappe.ValidationError):
			calendar.month_data(self.user, self.d(60), str(self.today), cells=True)

	def test_day_detail_and_edit_window(self):
		day = calendar.day_detail(self.user, self.d(1))
		states = {h["name"]: h["state"] for h in day["habits"]}
		self.assertEqual(states, {self.a: "done", self.b: "partial"})
		self.assertTrue(all(h["can_edit"] for h in day["habits"]))
		with self.assertRaises(frappe.ValidationError):
			calendar.day_detail(self.user, str(self.today + timedelta(days=1)))

	def test_habit_history_and_comebacks(self):
		h = calendar.habit_history(self.user, self.a, days=7)
		states = [c["state"] for c in h["cells"]]
		self.assertEqual(states, ["done", "done", "done", "missed", "done", "done", "pending"])
		self.assertEqual(h["week_rate"], 83)  # 5 of 6 (today pending isn't counted)
		self.assertEqual(h["comebacks"], 1)

	def test_insights_numbers(self):
		data = analytics.dashboard(self.user, 7)
		# A: 5 done / 6 scheduled; B: today done(1) + d1 partial + d6..d2 missed(5) -> 1/7
		self.assertEqual((data["completed"], data["scheduled"]), (6, 13))
		self.assertEqual(data["rate"], round(100 * 6 / 13))
		by = {h["name"]: h for h in data["habits"]}
		self.assertNotIn(self.c, by)
		self.assertEqual((by[self.a]["rate"], by[self.a]["missed"]), (83, 1))
		self.assertEqual(by[self.b]["missed"], 5)
		self.assertEqual(data["best"][0]["name"], self.a)
		self.assertEqual(data["struggling"][0]["name"], self.b)
		self.assertEqual({c["label"] for c in data["categories"]}, {"Health", "Reading"})
		self.assertEqual(len(data["heatmap"]), 365)
		self.assertEqual(len(data["trend"]), 7)
		self.assertEqual(data["comebacks"], 1)

	def test_range_limits_and_isolation(self):
		with self.assertRaises(frappe.ValidationError):
			calendar.month_data(self.user, str(self.today), self.d(5))
		with self.assertRaises(frappe.ValidationError):
			calendar.month_data(self.user, self.d(500), str(self.today))
		frappe.set_user(self.other)
		with self.assertRaises(frappe.DoesNotExistError):
			calendar.habit_history(self.other, self.a)
		with self.assertRaises(frappe.DoesNotExistError):
			calendar.month_data(self.other, self.d(6), str(self.today), habit=self.a)
		self.assertEqual(calendar.month_data(self.other, self.d(6), str(self.today))["habits"], [])
		self.assertEqual(analytics.dashboard(self.other)["scheduled"], 0)

	def test_pause_and_resume_track_periods(self):
		h = habits.create(self.user, {"habit_name": "Pausable", "start_date": self.d(6)})["name"]
		habits.set_status(self.user, h, "Paused")
		doc = frappe.get_doc("Atomic Habit", h)
		self.assertEqual(len(doc.pauses), 1)
		self.assertIsNone(doc.pauses[0].to_date)
		# today is paused: not scheduled, so not pending either
		self.assertNotIn(h, [x["name"] for x in calendar.day_detail(self.user, str(self.today))["habits"]])
		habits.set_status(self.user, h, "Active")  # same day: the pause leaves no gap
		self.assertEqual(len(frappe.get_doc("Atomic Habit", h).pauses), 0)

	def test_pause_from_earlier_days_is_closed_yesterday(self):
		h = habits.create(self.user, {"habit_name": "Was paused", "start_date": self.d(6)})["name"]
		doc = frappe.get_doc("Atomic Habit", h)
		doc.status = "Paused"
		doc.append("pauses", {"from_date": self.d(4)})
		doc.save(ignore_permissions=True)
		habits.set_status(self.user, h, "Active")
		p = frappe.get_doc("Atomic Habit", h).pauses
		self.assertEqual((str(p[0].from_date), str(p[0].to_date)), (self.d(4), self.d(1)))
		states = [c["state"] for c in calendar.habit_history(self.user, h, days=7)["cells"]]
		self.assertEqual(states, ["missed", "missed", "off", "off", "off", "off", "pending"])
