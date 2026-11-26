"""Day planner tests: tasks show up on their own day, carry-over, moving, limits and isolation.

Everything is created inside the test transaction and rolled back afterwards.

Run:  CI=1 bench --site <site> run-tests --module atomic_streak.tests.test_planner
"""

from datetime import timedelta

import frappe
from frappe.tests.utils import FrappeTestCase

from atomic_streak.constants import PLAN_TASK
from atomic_streak.services import planner
from atomic_streak.tests.test_ownership import ALICE, BOB, make_user
from atomic_streak.utils import user_today


class TestPlanner(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_user(ALICE)
		make_user(BOB)

	def setUp(self):
		frappe.set_user(ALICE)
		self.today = user_today(ALICE)

	def tearDown(self):
		frappe.set_user("Administrator")

	def day(self, offset=0):
		return str(self.today + timedelta(days=offset))

	def add(self, title, offset=0, **kw):
		return planner.save(ALICE, {"title": title, "plan_date": self.day(offset), **kw})

	def titles(self, view, key="tasks"):
		return [t["title"] for t in view[key]]

	# ------------------------------------------------------------------ planning ahead
	def test_tomorrow_task_appears_only_on_its_day(self):
		self.add("Plan-Tomorrow-Gym", 1)
		self.assertNotIn("Plan-Tomorrow-Gym", self.titles(planner.get_day(ALICE)))
		self.assertIn("Plan-Tomorrow-Gym", self.titles(planner.get_day(ALICE, self.day(1))))

	def test_future_dates_listed_as_upcoming(self):
		self.add("Plan-Far-A", 10)
		self.add("Plan-Far-B", 10, is_done=1)
		up = {u["date"]: u for u in planner.get_day(ALICE)["upcoming"]}
		self.assertGreaterEqual(up[self.day(10)]["total"], 2)
		self.assertGreaterEqual(up[self.day(10)]["done"], 1)

	def test_defaults_to_today_and_sorts_timed_first(self):
		untimed = planner.save(ALICE, {"title": "Plan-Sort-Untimed"})
		self.assertEqual(untimed["plan_date"], self.day())
		self.add("Plan-Sort-Late", start_time="18:00")
		self.add("Plan-Sort-Early", start_time="07:15")
		names = [t for t in self.titles(planner.get_day(ALICE)) if t.startswith("Plan-Sort-")]
		self.assertEqual(names, ["Plan-Sort-Early", "Plan-Sort-Late", "Plan-Sort-Untimed"])

	# ------------------------------------------------------------------ done / carry over / move
	def test_done_sets_and_clears_timestamp(self):
		t = self.add("Plan-Done")
		done = planner.set_done(ALICE, t["name"], True)
		self.assertEqual(done["is_done"], 1)
		self.assertTrue(done["done_at"])
		undone = planner.set_done(ALICE, t["name"], False)
		self.assertEqual(undone["is_done"], 0)
		self.assertIsNone(undone["done_at"])

	def test_unfinished_past_tasks_offered_on_today_only(self):
		open_task = self.add("Plan-Carry-Open", -2)
		self.add("Plan-Carry-Done", -2, is_done=1)
		self.assertIn("Plan-Carry-Open", self.titles(planner.get_day(ALICE), "carryover"))
		self.assertNotIn("Plan-Carry-Done", self.titles(planner.get_day(ALICE), "carryover"))
		self.assertEqual(planner.get_day(ALICE, self.day(1))["carryover"], [])

		res = planner.move(ALICE, [open_task["name"]], self.day())
		self.assertEqual(res["moved"], 1)
		view = planner.get_day(ALICE)
		self.assertIn("Plan-Carry-Open", self.titles(view))
		self.assertNotIn("Plan-Carry-Open", self.titles(view, "carryover"))

	def test_edit_can_move_to_another_day(self):
		t = self.add("Plan-Reschedule")
		planner.save(ALICE, {"plan_date": self.day(3)}, t["name"])
		self.assertIn("Plan-Reschedule", self.titles(planner.get_day(ALICE, self.day(3))))
		self.assertNotIn("Plan-Reschedule", self.titles(planner.get_day(ALICE)))

	# ------------------------------------------------------------------ validation
	def test_date_range_and_text_limits(self):
		with self.assertRaises(frappe.ValidationError):
			self.add("Too far", planner.DAYS_AHEAD + 1)
		with self.assertRaises(frappe.ValidationError):
			self.add("Too old", -(planner.DAYS_BACK + 1))
		with self.assertRaises(frappe.ValidationError):
			self.add("  ")
		with self.assertRaises(frappe.ValidationError):
			self.add("Bad time", start_time="25:00")
		with self.assertRaises(frappe.ValidationError):
			planner.save(ALICE, {"title": "Bad date", "plan_date": "not-a-date"})
		self.assertEqual(self.add("<b>Plan-Markup</b>")["title"], "Plan-Markup")

	def test_day_capacity(self):
		day = 40
		for i in range(planner.MAX_PER_DAY):
			frappe.get_doc({"doctype": PLAN_TASK, "title": f"bulk {i}", "plan_date": self.day(day)}).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			self.add("One too many", day)

	# ------------------------------------------------------------------ isolation
	def test_other_users_tasks_are_invisible_and_untouchable(self):
		t = self.add("Plan-Alice-Private")
		frappe.set_user(BOB)
		self.assertNotIn("Plan-Alice-Private", self.titles(planner.get_day(BOB)))
		for action in (
			lambda: planner.save(BOB, {"title": "hijack"}, t["name"]),
			lambda: planner.set_done(BOB, t["name"], True),
			lambda: planner.move(BOB, [t["name"]], self.day(1)),
			lambda: planner.delete(BOB, t["name"]),
		):
			with self.assertRaises(frappe.DoesNotExistError):
				action()
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc({"doctype": PLAN_TASK, "user": ALICE, "title": "x", "plan_date": self.day()}).insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists(PLAN_TASK, t["name"]))
