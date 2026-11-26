"""Habit service tests: check-ins, recalculation, whitelisting and isolation.

Run:  CI=1 bench --site <site> run-tests --module atomic_streak.tests.test_habits
"""

from datetime import timedelta

import frappe
from frappe.tests.utils import FrappeTestCase

from atomic_streak.constants import COMPLETION, HABIT, PROFILE
from atomic_streak.services import accounts, habits
from atomic_streak.utils import user_today

DOMAIN = "atomicstreak.test"
PASSWORD = "Lantern-Orbit-93!"


class TestHabits(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.db.set_single_value("Atomic Streak Settings", "allow_signup", 1)
		cls.amy = accounts.create_account("Amy Habit", f"amy@{DOMAIN}", PASSWORD, "Asia/Kolkata")
		cls.ben = accounts.create_account("Ben Habit", f"ben.h@{DOMAIN}", PASSWORD, "Asia/Kolkata")

	def setUp(self):
		frappe.set_user(self.amy)
		self.today = user_today(self.amy)

	def tearDown(self):
		frappe.set_user("Administrator")

	def new(self, **kw):
		data = {"habit_name": "Read", "start_date": str(self.today - timedelta(days=20)), **kw}
		return habits.create(self.amy, data)

	# ------------------------------------------------------------- create/update
	def test_whitelist_ignores_protected_fields(self):
		h = self.new(current_streak=999, total_completions=50, user=self.ben, status="Completed", weekdays=["Monday"])
		self.assertEqual((h["current_streak"], h["total_completions"], h["status"]), (0, 0, "Active"))
		self.assertEqual(frappe.db.get_value(HABIT, h["name"], "user"), self.amy)
		self.assertEqual(h["weekdays"], [])  # Daily habits keep no weekdays

	def test_specific_days_round_trip_and_sort_order(self):
		a = self.new(frequency="Specific Days", weekdays=["Friday", "Monday"])
		b = self.new(habit_name="Walk")
		self.assertEqual(a["weekdays"], ["Monday", "Friday"])
		self.assertGreater(b["sort_order"], a["sort_order"])
		updated = habits.update(self.amy, a["name"], {"weekdays": ["Sunday"], "habit_name": "Read more"})
		self.assertEqual((updated["weekdays"], updated["habit_name"]), (["Sunday"], "Read more"))

	def test_other_users_habit_is_not_found(self):
		h = self.new()
		frappe.set_user(self.ben)
		for call in (
			lambda: habits.get_habit(h["name"], self.ben),
			lambda: habits.update(self.ben, h["name"], {"habit_name": "x"}),
			lambda: habits.check_in(self.ben, h["name"]),
			lambda: habits.delete(self.ben, h["name"]),
		):
			with self.assertRaises(frappe.DoesNotExistError):
				call()
		self.assertNotIn(h["name"], [x["name"] for x in habits.list_habits(self.ben, "all")])

	# ------------------------------------------------------------- check-ins
	def test_check_in_updates_streaks_and_profile(self):
		h = self.new()
		for n in (2, 1, 0):
			r = habits.check_in(self.amy, h["name"], self.today - timedelta(days=n))
		self.assertEqual(r["stats"]["current_streak"], 3)
		self.assertEqual(r["streak"]["current"], 3)
		self.assertEqual(frappe.db.get_value(PROFILE, self.amy, "total_completions"), 3)

	def test_editing_history_recalculates(self):
		h = self.new()
		for n in (3, 2, 1, 0):
			habits.check_in(self.amy, h["name"], self.today - timedelta(days=n))
		r = habits.undo_check_in(self.amy, h["name"], self.today - timedelta(days=2))
		self.assertEqual((r["stats"]["current_streak"], r["stats"]["longest_streak"]), (2, 2))
		self.assertEqual(r["stats"]["total_completions"], 3)

	def test_partial_then_complete_same_record(self):
		h = self.new(daily_target=8, target_unit="glasses")
		r = habits.check_in(self.amy, h["name"], value=3)
		self.assertEqual((r["completion"]["status"], r["stats"]["current_streak"]), ("Partial", 0))
		r2 = habits.check_in(self.amy, h["name"], value=8)
		self.assertEqual(r2["completion"]["name"], r["completion"]["name"])
		self.assertEqual((r2["completion"]["status"], r2["stats"]["current_streak"]), ("Completed", 1))
		self.assertEqual(frappe.db.count(COMPLETION, {"habit": h["name"]}), 1)

	def test_client_id_resend_is_idempotent(self):
		h = self.new(daily_target=5)
		first = habits.check_in(self.amy, h["name"], value=5, client_id="offline-0001-abcd", source="Offline")
		again = habits.check_in(self.amy, h["name"], value=2, client_id="offline-0001-abcd", source="Offline")
		self.assertEqual(first["completion"], again["completion"])
		self.assertEqual(again["completion"]["value"], 5)  # a re-send never overwrites
		self.assertEqual(frappe.db.count(COMPLETION, {"habit": h["name"]}), 1)

	def test_client_id_adopted_by_existing_check_in(self):
		"""Partial check-in first (no id), then a device completes it with an id, then re-sends."""
		h = self.new(daily_target=8)
		habits.check_in(self.amy, h["name"], value=3)
		habits.check_in(self.amy, h["name"], value=8, client_id="device-xyz-0002")
		again = habits.check_in(self.amy, h["name"], value=1, client_id="device-xyz-0002")
		self.assertEqual((again["completion"]["value"], again["completion"]["status"]), (8, "Completed"))

	def test_foreign_client_id_rejected(self):
		h = self.new()
		habits.check_in(self.amy, h["name"], client_id="shared-id-0000-1")
		frappe.set_user(self.ben)
		bh = habits.create(self.ben, {"habit_name": "Ben's"})
		with self.assertRaises(frappe.ValidationError):
			habits.check_in(self.ben, bh["name"], client_id="shared-id-0000-1")

	def test_one_time_goal_completes_and_reopens(self):
		h = self.new(habit_type="One-time", habit_name="Book dentist")
		r = habits.check_in(self.amy, h["name"])
		self.assertEqual(r["stats"]["status"], "Completed")
		self.assertIn(h["name"], [x["name"] for x in habits.today_view(self.amy)["habits"]])
		r = habits.undo_check_in(self.amy, h["name"])
		self.assertEqual(r["stats"]["status"], "Active")

	def test_paused_habit_rejects_check_in_and_leaves_today(self):
		h = self.new()
		habits.set_status(self.amy, h["name"], "Paused")
		self.assertNotIn(h["name"], [x["name"] for x in habits.today_view(self.amy)["habits"]])
		with self.assertRaises(frappe.ValidationError):
			habits.check_in(self.amy, h["name"])

	# ------------------------------------------------------------- views
	def test_today_view_only_due_habits_and_summary(self):
		weekday = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
		due = self.new(habit_name="Due")
		not_due = self.new(habit_name="Not today", frequency="Specific Days", weekdays=[weekday[(self.today.weekday() + 1) % 7]])
		habits.check_in(self.amy, due["name"])
		view = habits.today_view(self.amy)
		names = [x["name"] for x in view["habits"]]
		self.assertIn(due["name"], names)
		self.assertNotIn(not_due["name"], names)
		self.assertEqual(view["date"], str(self.today))
		s = view["summary"]
		self.assertEqual(s["completed"] + s["remaining"], s["total"])
		self.assertEqual(len(view["week"]), 7)
		self.assertTrue(any(day["is_today"] for day in view["week"]))
		with self.assertRaises(frappe.ValidationError):
			habits.today_view(self.amy, self.today + timedelta(days=1))

	def test_today_view_orders_by_part_of_day_with_night(self):
		made = {t: self.new(habit_name=f"{t} habit", time_of_day=t)["name"] for t in ("Anytime", "Night", "Evening", "Morning", "Afternoon")}
		self.assertEqual(frappe.db.get_value(HABIT, made["Night"], "time_of_day"), "Night")
		order = [x["time_of_day"] for x in habits.today_view(self.amy)["habits"] if x["name"] in made.values()]
		self.assertEqual(order, ["Morning", "Afternoon", "Evening", "Night", "Anytime"])

	def test_reorder_ignores_foreign_names(self):
		a, b = self.new(habit_name="A"), self.new(habit_name="B")
		frappe.set_user(self.ben)
		bh = habits.create(self.ben, {"habit_name": "Ben's"})
		before = frappe.db.get_value(HABIT, bh["name"], "sort_order")
		frappe.set_user(self.amy)
		habits.reorder(self.amy, [b["name"], bh["name"], a["name"]])
		self.assertEqual(frappe.db.get_value(HABIT, bh["name"], "sort_order"), before)
		self.assertLess(frappe.db.get_value(HABIT, b["name"], "sort_order"), frappe.db.get_value(HABIT, a["name"], "sort_order"))

	def test_categories_private(self):
		cat = habits.create_category(self.amy, "Guitar practice", "music", "#26C281")
		frappe.set_user(self.ben)
		self.assertNotIn(cat["name"], [c["name"] for c in habits.list_categories(self.ben)])
		self.assertIn("Health", [c["name"] for c in habits.list_categories(self.ben)])
		with self.assertRaises(frappe.DoesNotExistError):
			habits.delete_category(self.ben, cat["name"])

	def test_delete_habit_updates_profile(self):
		h = self.new()
		habits.check_in(self.amy, h["name"])
		before = frappe.db.get_value(PROFILE, self.amy, "total_completions")  # other tests' check-ins too
		habits.delete(self.amy, h["name"])
		self.assertFalse(frappe.db.exists(HABIT, h["name"]))
		self.assertEqual(frappe.db.get_value(PROFILE, self.amy, "total_completions"), before - 1)
