"""Data isolation and validation tests for the Atomic Streak DocTypes.

Inserts use ignore_permissions=True exactly like atomic_streak.api.* does: app users have
no DocType permissions, so these tests exercise the controller-level ownership rules.

Everything is created inside the test transaction and rolled back afterwards (FrappeTestCase),
and the module declares no test dependencies, so no fixture records are committed.

Run:  CI=1 bench --site <site> run-tests --module atomic_streak.tests.test_ownership
"""

from datetime import timedelta

import frappe
from frappe.tests.utils import FrappeTestCase

from atomic_streak.constants import (
	CATEGORY,
	COMPLETION,
	HABIT,
	PROFILE,
	ROLE_USER,
	ROUTINE,
	USER_OWNED,
	CompletionStatus,
)
from atomic_streak.setup import install
from atomic_streak.utils import user_today

DOMAIN = "atomicstreak.test"
ALICE, BOB = f"alice@{DOMAIN}", f"bob@{DOMAIN}"


def make_user(email):
	if frappe.db.exists("User", email):
		return frappe.get_doc("User", email)
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": email.split("@")[0].title(),
			"user_type": "Website User",
			"send_welcome_email": 0,
		}
	)
	user.flags.no_welcome_mail = True
	user.append("roles", {"role": ROLE_USER})
	user.insert(ignore_permissions=True)
	return user


def make_habit(**kw):
	doc = frappe.get_doc({"doctype": HABIT, "habit_name": "Read", "start_date": user_today() - timedelta(days=30), **kw})
	return doc.insert(ignore_permissions=True)


def complete(habit, day=None, **kw):
	return frappe.get_doc(
		{"doctype": COMPLETION, "habit": habit, "completion_date": day or user_today(), **kw}
	).insert(ignore_permissions=True)


class TestOwnership(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_user(ALICE)
		make_user(BOB)

	def tearDown(self):
		frappe.set_user("Administrator")

	# ------------------------------------------------------------------ ownership
	def test_owner_defaults_to_session_user(self):
		frappe.set_user(ALICE)
		self.assertEqual(make_habit().user, ALICE)

	def test_cannot_create_for_another_user(self):
		frappe.set_user(ALICE)
		with self.assertRaises(frappe.PermissionError):
			make_habit(user=BOB)

	def test_cannot_edit_or_delete_another_users_habit(self):
		frappe.set_user(BOB)
		habit = make_habit()
		frappe.set_user(ALICE)
		doc = frappe.get_doc(HABIT, habit.name)
		doc.habit_name = "Hacked"
		with self.assertRaises(frappe.PermissionError):
			doc.save(ignore_permissions=True)
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc(HABIT, habit.name, ignore_permissions=True)

	def test_cannot_move_record_to_another_user(self):
		frappe.set_user(ALICE)
		habit = make_habit()
		frappe.set_user("Administrator")
		habit.reload()
		habit.user = BOB
		with self.assertRaises(frappe.PermissionError):
			habit.save()

	def test_cannot_check_in_on_someone_elses_habit(self):
		frappe.set_user(BOB)
		habit = make_habit()
		frappe.set_user(ALICE)
		with self.assertRaises(frappe.DoesNotExistError):
			complete(habit.name)

	def test_routine_cannot_reference_foreign_habit(self):
		frappe.set_user(BOB)
		bobs = make_habit()
		frappe.set_user(ALICE)
		with self.assertRaises(frappe.DoesNotExistError):
			frappe.get_doc(
				{"doctype": ROUTINE, "routine_name": "Morning", "items": [{"habit": bobs.name}]}
			).insert(ignore_permissions=True)

	def test_app_users_have_no_direct_doctype_access(self):
		"""End users only reach data through atomic_streak.api.*, never /api/resource or Desk."""
		for doctype in (*USER_OWNED, CATEGORY):
			self.assertFalse(frappe.has_permission(doctype, "read", user=ALICE), doctype)
			self.assertFalse(frappe.has_permission(doctype, "create", user=ALICE), doctype)
		frappe.set_user(ALICE)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_list(HABIT)

	# ------------------------------------------------------------------ categories
	def test_custom_category_is_private(self):
		frappe.set_user(ALICE)
		cat = frappe.get_doc({"doctype": CATEGORY, "category_name": "Guitar"}).insert(ignore_permissions=True)
		self.assertEqual(cat.user, ALICE)
		self.assertFalse(cat.is_standard)
		make_habit(category=cat.name)
		make_habit(category="Health")  # built-in categories are shared
		frappe.set_user(BOB)
		with self.assertRaises(frappe.DoesNotExistError):
			make_habit(category=cat.name)

	def test_category_name_cannot_duplicate_builtin(self):
		frappe.set_user(ALICE)
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": CATEGORY, "category_name": "health"}).insert(ignore_permissions=True)

	def test_user_cannot_create_standard_category(self):
		frappe.set_user(ALICE)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc({"doctype": CATEGORY, "category_name": "Mine", "is_standard": 1}).insert(ignore_permissions=True)

	# ------------------------------------------------------------------ completions
	def test_one_completion_per_habit_per_day(self):
		frappe.set_user(ALICE)
		habit = make_habit()
		complete(habit.name)
		with self.assertRaises(frappe.DuplicateEntryError):
			complete(habit.name)

	def test_unique_index_blocks_duplicates_even_without_validation(self):
		frappe.set_user(ALICE)
		habit = make_habit()
		first = complete(habit.name)
		dup = frappe.copy_doc(first)
		dup.client_id = None
		dup.set_new_name()
		with self.assertRaises(frappe.UniqueValidationError):
			dup.db_insert()

	def test_client_id_makes_resends_idempotent_at_db_level(self):
		frappe.set_user(ALICE)
		h1, h2 = make_habit(), make_habit(habit_name="Walk")
		complete(h1.name, client_id="device-abc-123")
		with self.assertRaises(frappe.UniqueValidationError):
			complete(h2.name, client_id="device-abc-123")

	def test_future_and_old_dates_rejected(self):
		frappe.set_user(ALICE)
		habit = make_habit()
		with self.assertRaises(frappe.ValidationError):
			complete(habit.name, user_today() + timedelta(days=1))
		with self.assertRaises(frappe.ValidationError):
			complete(habit.name, user_today() - timedelta(days=8))
		complete(habit.name, user_today() - timedelta(days=7))  # inside the backfill window

	def test_partial_vs_completed(self):
		frappe.set_user(ALICE)
		habit = make_habit(daily_target=10, target_unit="pages")
		partial = complete(habit.name, value=4)
		self.assertEqual(partial.status, CompletionStatus.PARTIAL)
		self.assertEqual(partial.target, 10)
		full = complete(habit.name, user_today() - timedelta(days=1), value=12)
		self.assertEqual(full.status, CompletionStatus.COMPLETED)

	def test_paused_habit_cannot_be_checked_in(self):
		frappe.set_user(ALICE)
		habit = make_habit(status="Paused")
		with self.assertRaises(frappe.ValidationError):
			complete(habit.name)

	# ------------------------------------------------------------------ habit rules
	def test_specific_days_needs_a_weekday_and_is_normalised(self):
		frappe.set_user(ALICE)
		with self.assertRaises(frappe.ValidationError):
			make_habit(frequency="Specific Days")
		habit = make_habit(
			frequency="Specific Days",
			schedule=[{"weekday": "Friday"}, {"weekday": "Monday"}, {"weekday": "Friday"}],
		)
		self.assertEqual([r.weekday for r in habit.schedule], ["Monday", "Friday"])

	def test_times_are_optional_hh_mm(self):
		frappe.set_user(ALICE)
		habit = make_habit()
		self.assertIsNone(habit.reminder_time)
		self.assertIsNone(habit.preferred_time)
		habit = make_habit(reminder_enabled=1, reminder_time="07:30:00", preferred_time="21:05")
		self.assertEqual((habit.reminder_time, habit.preferred_time), ("07:30", "21:05"))

	def test_break_habit_is_one_check_in_per_day(self):
		frappe.set_user(ALICE)
		habit = make_habit(habit_type="Break", daily_target=5)
		self.assertEqual((habit.daily_target, habit.target_unit), (1, "day"))

	def test_bad_input_rejected(self):
		frappe.set_user(ALICE)
		for bad in (
			{"color": "red; background:url(x)"},
			{"icon": "<script>"},
			{"daily_target": 0},
			{"habit_name": "   "},
			{"reminder_enabled": 1},
			{"reminder_enabled": 1, "reminder_time": "25:00"},
			{"preferred_time": "7pm"},
			{"end_date": user_today() - timedelta(days=60)},
		):
			with self.subTest(bad=bad), self.assertRaises(frappe.ValidationError):
				make_habit(**bad)

	# ------------------------------------------------------------------ lifecycle
	def test_deleting_habit_removes_its_history(self):
		frappe.set_user(ALICE)
		habit = make_habit()
		complete(habit.name)
		frappe.get_doc({"doctype": ROUTINE, "routine_name": "AM", "items": [{"habit": habit.name}]}).insert(ignore_permissions=True)
		frappe.delete_doc(HABIT, habit.name, ignore_permissions=True)
		self.assertFalse(frappe.db.exists(COMPLETION, {"habit": habit.name}))
		self.assertFalse(frappe.db.exists("Atomic Habit Routine Item", {"habit": habit.name}))

	def test_deleting_user_removes_all_their_data(self):
		email = f"carol@{DOMAIN}"
		make_user(email)
		frappe.set_user(email)
		habit = make_habit()
		complete(habit.name)
		frappe.get_doc({"doctype": PROFILE, "timezone": "Asia/Kolkata"}).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": CATEGORY, "category_name": "Carol's"}).insert(ignore_permissions=True)
		frappe.set_user("Administrator")
		frappe.delete_doc("User", email)
		for doctype in USER_OWNED:
			self.assertFalse(frappe.db.exists(doctype, {"user": email}), doctype)
		self.assertFalse(frappe.db.exists(CATEGORY, {"user": email}))

	def test_profile_rejects_unknown_timezone(self):
		frappe.set_user(ALICE)
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": PROFILE, "timezone": "Mars/Olympus"}).insert(ignore_permissions=True)


class TestInstall(FrappeTestCase):
	def test_setup_is_idempotent(self):
		before = {dt: frappe.db.count(dt) for dt in (CATEGORY, "Atomic Achievement", "Atomic Challenge", "Role")}
		install.setup()
		install.setup()
		after = {dt: frappe.db.count(dt) for dt in before}
		self.assertEqual(before, after)
		self.assertTrue(frappe.db.exists("Role", ROLE_USER))
		self.assertEqual(frappe.db.count(CATEGORY, {"is_standard": 1}), len(install.CATEGORIES))
