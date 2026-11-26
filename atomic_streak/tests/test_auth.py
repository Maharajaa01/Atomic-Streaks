"""Sign-up, join, password-reset and boot tests.

Calls the service layer (the whitelisted wrappers only add rate limits and login_as).
Email sending is mocked; everything is rolled back after the class.

Run:  CI=1 bench --site <site> run-tests --module atomic_streak.tests.test_auth
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from atomic_streak.api import auth as auth_api
from atomic_streak.api import session as session_api
from atomic_streak.constants import PROFILE, ROLE_USER, SETTINGS
from atomic_streak.services import accounts

DOMAIN = "atomicstreak.test"
GOOD_PASSWORD = "Lantern-Orbit-93!"


def set_signup(enabled: int):
	frappe.db.set_single_value(SETTINGS, "allow_signup", enabled)
	frappe.clear_document_cache(SETTINGS, SETTINGS)


class TestSignup(FrappeTestCase):
	def setUp(self):
		set_signup(1)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_creates_website_user_with_role_profile_and_timezone(self):
		user = accounts.create_account("Priya Raman", "Priya@Atomicstreak.Test ", GOOD_PASSWORD, "Asia/Kolkata")
		self.assertEqual(user, f"priya@{DOMAIN}")
		doc = frappe.get_doc("User", user)
		self.assertEqual(doc.user_type, "Website User")
		self.assertEqual((doc.first_name, doc.last_name), ("Priya", "Raman"))
		self.assertIn(ROLE_USER, frappe.get_roles(user))
		self.assertNotIn("System Manager", frappe.get_roles(user))
		profile = frappe.get_doc(PROFILE, user)
		self.assertEqual((profile.user, profile.timezone, profile.full_name), (user, "Asia/Kolkata", "Priya Raman"))
		# the password works through Frappe's own check
		from frappe.utils.password import check_password

		self.assertEqual(check_password(user, GOOD_PASSWORD), user)

	def test_unknown_timezone_is_ignored_not_fatal(self):
		user = accounts.create_account("Tz Test", f"tz@{DOMAIN}", GOOD_PASSWORD, "Not/AZone")
		self.assertIsNone(frappe.db.get_value(PROFILE, user, "timezone"))

	def test_duplicate_email(self):
		accounts.create_account("Dup One", f"dup@{DOMAIN}", GOOD_PASSWORD)
		with self.assertRaises(frappe.DuplicateEntryError):
			accounts.create_account("Dup Two", f"DUP@{DOMAIN}", GOOD_PASSWORD)

	def test_rejects_bad_input(self):
		cases = [
			("", f"a@{DOMAIN}", GOOD_PASSWORD),
			("Name", "not-an-email", GOOD_PASSWORD),
			("Name", f"b@{DOMAIN}", "short"),
			("Name", f"c@{DOMAIN}", "x" * 101),
			("N" * 141, f"d@{DOMAIN}", GOOD_PASSWORD),
		]
		for name, email, password in cases:
			with self.subTest(email=email), self.assertRaises(frappe.ValidationError):
				accounts.create_account(name, email, password)

	def test_signup_closed(self):
		set_signup(0)
		with self.assertRaises(frappe.PermissionError):
			accounts.create_account("Closed", f"closed@{DOMAIN}", GOOD_PASSWORD)
		self.assertFalse(auth_api.get_auth_options()["allow_signup"])

	def test_register_refuses_signed_in_user(self):
		user = accounts.create_account("Signed In", f"in@{DOMAIN}", GOOD_PASSWORD)
		frappe.set_user(user)
		with self.assertRaises(frappe.ValidationError):
			auth_api.register("X", f"x2@{DOMAIN}", GOOD_PASSWORD)


class TestJoinAndBoot(FrappeTestCase):
	def setUp(self):
		set_signup(1)

	def tearDown(self):
		frappe.set_user("Administrator")

	def make_plain_user(self, email):
		doc = frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "Erp", "send_welcome_email": 0, "user_type": "Website User"}
		)
		doc.flags.no_welcome_mail = True
		return doc.insert(ignore_permissions=True).name

	def test_boot_requires_login(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			session_api.get_boot()

	def test_existing_account_can_join(self):
		user = self.make_plain_user(f"erp@{DOMAIN}")
		frappe.set_user(user)
		boot = session_api.get_boot()
		self.assertFalse(boot["has_access"])
		self.assertNotIn("profile", boot)

		auth_api.join(timezone="Europe/London")
		boot = session_api.get_boot()
		self.assertTrue(boot["has_access"])
		self.assertEqual(boot["profile"]["timezone"], "Europe/London")
		self.assertTrue(boot["profile"]["has_timezone"])
		self.assertEqual(frappe.db.get_value("User", user, "user_type"), "Website User")  # no Desk access gained

	def test_join_closed(self):
		user = self.make_plain_user(f"late@{DOMAIN}")
		set_signup(0)
		frappe.set_user(user)
		with self.assertRaises(frappe.PermissionError):
			auth_api.join()

	def test_boot_only_shows_own_profile(self):
		a = accounts.create_account("Ann One", f"ann@{DOMAIN}", GOOD_PASSWORD, "Asia/Tokyo")
		accounts.create_account("Ben Two", f"ben@{DOMAIN}", GOOD_PASSWORD, "America/New_York")
		frappe.set_user(a)
		boot = session_api.get_boot()
		self.assertEqual(boot["user"], a)
		self.assertEqual(boot["profile"]["full_name"], "Ann One")
		self.assertEqual(boot["profile"]["timezone"], "Asia/Tokyo")


class TestPasswordReset(FrappeTestCase):
	# rollback happens once per class, so the account is created once too
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		set_signup(1)
		cls.user = accounts.create_account("Reset Me", f"reset@{DOMAIN}", GOOD_PASSWORD)

	@patch("frappe.sendmail")
	def test_sends_app_link_and_stores_only_hashed_key(self, sendmail):
		accounts.send_password_reset(f"  RESET@{DOMAIN} ")
		sendmail.assert_called_once()
		kwargs = sendmail.call_args.kwargs
		self.assertEqual(kwargs["recipients"], [self.user])
		self.assertIn("/atomic-streak/reset-password?key=", kwargs["message"])
		key = kwargs["message"].split("key=", 1)[1].split('"', 1)[0]
		stored = frappe.db.get_value("User", self.user, "reset_password_key")
		self.assertTrue(stored)
		self.assertNotEqual(stored, key)  # Frappe keeps only the sha256 of the key
		from frappe.utils.data import sha256_hash

		self.assertEqual(stored, sha256_hash(key))

	@patch("frappe.sendmail")
	def test_silent_for_unknown_and_non_app_accounts(self, sendmail):
		accounts.send_password_reset(f"nobody@{DOMAIN}")
		accounts.send_password_reset("Administrator")
		accounts.send_password_reset("not an email")
		other = frappe.get_doc(
			{"doctype": "User", "email": f"erp-only@{DOMAIN}", "first_name": "Erp", "send_welcome_email": 0}
		)
		other.flags.no_welcome_mail = True
		other.insert(ignore_permissions=True)
		accounts.send_password_reset(other.name)
		sendmail.assert_not_called()

	@patch("frappe.sendmail")
	def test_api_answers_identically(self, sendmail):
		# (outside an HTTP request the rate limiter is a no-op, so this calls the endpoint directly)
		known = auth_api.request_password_reset(f"reset@{DOMAIN}")
		unknown = auth_api.request_password_reset(f"nobody@{DOMAIN}")
		self.assertEqual(known, unknown)
		self.assertEqual(sendmail.call_count, 1)
