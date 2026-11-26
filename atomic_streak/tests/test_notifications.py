"""Phase 7 tests: push subscriptions, sending, reminder scheduling and offline-sync conflicts.

Run:  CI=1 bench --site <site> run-tests --module atomic_streak.tests.test_notifications

Nothing is sent over the network: pywebpush.webpush is replaced by a fake.
"""

from datetime import datetime, time, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
from zoneinfo import ZoneInfo

import frappe
from frappe.tests.utils import FrappeTestCase

from atomic_streak.constants import COMPLETION, PROFILE, SETTINGS, SUBSCRIPTION
from atomic_streak.services import accounts, challenges, habits, push, reminders
from atomic_streak.utils import user_today

DOMAIN = "atomicstreak.test"
PASSWORD = "Lantern-Orbit-93!"
TZ = "Asia/Kolkata"
FCM = "https://fcm.googleapis.com/fcm/send/"


def sub(n="a"):
	return {"endpoint": FCM + n * 20, "keys": {"p256dh": "BPk" + n * 40, "auth": "au" + n * 10}}


class FakePush:
	"""Stands in for pywebpush.webpush; records calls and can fail with a status code."""

	def __init__(self, status=None):
		self.calls, self.status = [], status

	def __call__(self, subscription_info, data=None, **kw):
		self.calls.append(frappe.parse_json(data) | {"endpoint": subscription_info["endpoint"]})
		if self.status:
			from pywebpush import WebPushException

			raise WebPushException("push failed", response=SimpleNamespace(status_code=self.status, text=""))


def local(hh, mm, day_offset=0, tz=TZ):
	"""A UTC instant that is hh:mm today (+offset) in `tz`."""
	z = ZoneInfo(tz)
	d = datetime.now(z).date() + timedelta(days=day_offset)
	return datetime.combine(d, time(hh, mm), tzinfo=z).astimezone(timezone.utc)


class TestNotifications(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.db.set_single_value(SETTINGS, {"allow_signup": 1, "push_enabled": 1})
		push.ensure_vapid_keys()
		frappe.clear_document_cache(SETTINGS, SETTINGS)

	def setUp(self):
		frappe.set_user("Administrator")
		# unique per run: the "already sent today" keys live in Redis, outside the test rollback
		tag = frappe.generate_hash(length=8)
		self.amy = accounts.create_account("Amy Push", f"amy.{tag}@{DOMAIN}", PASSWORD, TZ)
		self.ben = accounts.create_account("Ben Push", f"ben.{tag}@{DOMAIN}", PASSWORD, TZ)
		frappe.set_user(self.amy)
		self.today = user_today(self.amy)

	def tearDown(self):
		frappe.set_user("Administrator")

	def habit(self, **kw):
		return habits.create(self.amy, {"habit_name": "Read", "start_date": str(self.today - timedelta(days=10)), **kw})

	# ------------------------------------------------------------- endpoint safety
	def test_only_real_push_services_are_accepted(self):
		ok = [
			"https://fcm.googleapis.com/fcm/send/abc",
			"https://jmt17.google.com/fcm/send/abc",
			"https://updates.push.services.mozilla.com/wpush/v2/abc",
			"https://web.push.apple.com/abc",
			"https://wns2-par02p.notify.windows.com/w/?token=abc",
		]
		bad = [
			"http://fcm.googleapis.com/fcm/send/abc",
			"https://fcm.googleapis.com.evil.com/x",
			"https://evil.com/fcm.googleapis.com",
			"https://evilgoogle.com/fcm/send/x",
			"https://google.com.evil.com/x",
			"https://fcm.googleapis.com:8443/x",
			"https://localhost/x",
			"https://127.0.0.1/x",
			"https://admin.dreamtechsolution.com/api/method/x",
			"javascript:alert(1)",
			"",
		]
		self.assertTrue(all(push.is_push_endpoint(u) for u in ok))
		self.assertFalse(any(push.is_push_endpoint(u) for u in bad))
		with self.assertRaises(frappe.ValidationError):
			push.subscribe(self.amy, {"endpoint": "https://evil.com/hook", "keys": {"p256dh": "x", "auth": "y"}})

	# ------------------------------------------------------------- subscriptions
	def test_subscribe_is_idempotent_and_moves_between_accounts(self):
		push.subscribe(self.amy, sub("a"), "Chrome")
		push.subscribe(self.amy, sub("a"), "Chrome")
		self.assertEqual(frappe.db.count(SUBSCRIPTION, {"user": self.amy}), 1)
		self.assertTrue(push.has_active(self.amy))
		# the same browser signs in as Ben: Amy must stop receiving on it
		frappe.set_user(self.ben)
		push.subscribe(self.ben, sub("a"), "Chrome")
		self.assertEqual(frappe.db.count(SUBSCRIPTION, {"user": self.amy}), 0)
		self.assertEqual(frappe.db.count(SUBSCRIPTION, {"user": self.ben}), 1)

	def test_subscription_cap_and_unsubscribe_is_own_only(self):
		for i in range(push.MAX_SUBSCRIPTIONS + 2):
			push.subscribe(self.amy, sub(chr(97 + i)))
		self.assertEqual(frappe.db.count(SUBSCRIPTION, {"user": self.amy}), push.MAX_SUBSCRIPTIONS)
		push.unsubscribe(self.ben, sub("l")["endpoint"])  # not Ben's
		self.assertEqual(frappe.db.count(SUBSCRIPTION, {"user": self.amy}), push.MAX_SUBSCRIPTIONS)
		push.unsubscribe(self.amy, sub("l")["endpoint"])
		self.assertEqual(frappe.db.count(SUBSCRIPTION, {"user": self.amy}), push.MAX_SUBSCRIPTIONS - 1)

	# ------------------------------------------------------------- sending
	def test_send_success_and_payload(self):
		push.subscribe(self.amy, sub("a"))
		fake = FakePush()
		with patch("pywebpush.webpush", fake):
			self.assertEqual(push.send(self.amy, "Hi", "Body", url="/atomic-streak/x", tag="t1"), 1)
		self.assertEqual(fake.calls[0] | {"endpoint": None}, {"title": "Hi", "body": "Body", "url": "/atomic-streak/x", "tag": "t1", "kind": "reminder", "endpoint": None})
		self.assertTrue(frappe.db.get_value(SUBSCRIPTION, {"user": self.amy}, "last_success"))

	def test_gone_subscription_is_switched_off_and_errors_counted(self):
		push.subscribe(self.amy, sub("a"))
		with patch("pywebpush.webpush", FakePush(500)), patch("frappe.log_error"):
			push.send(self.amy, "x", "y")
		self.assertEqual(frappe.db.get_value(SUBSCRIPTION, {"user": self.amy}, ["failure_count", "is_active"]), (1, 1))
		with patch("pywebpush.webpush", FakePush(410)):
			push.send(self.amy, "x", "y")
		self.assertEqual(frappe.db.get_value(SUBSCRIPTION, {"user": self.amy}, "is_active"), 0)
		with patch("pywebpush.webpush", FakePush()) as fake:
			self.assertEqual(push.send(self.amy, "x", "y"), 0)
		self.assertEqual(fake.calls, [])

	def test_nothing_sent_when_push_is_off(self):
		push.subscribe(self.amy, sub("a"))
		frappe.db.set_single_value(SETTINGS, "push_enabled", 0)
		frappe.clear_document_cache(SETTINGS, SETTINGS)
		try:
			with patch("pywebpush.webpush", FakePush()) as fake:
				self.assertEqual(push.send(self.amy, "x", "y"), 0)
			self.assertEqual(fake.calls, [])
		finally:
			frappe.db.set_single_value(SETTINGS, "push_enabled", 1)
			frappe.clear_document_cache(SETTINGS, SETTINGS)

	def test_new_profile_daily_reminder_is_eight_not_signup_time(self):
		self.assertEqual(str(frappe.db.get_value(PROFILE, self.amy, "daily_reminder_time")), "8:00:00")

	# ------------------------------------------------------------- reminders
	def run_at(self, when):
		with patch.object(push, "send", return_value=1) as send:
			sent = reminders.process_user(self.amy, when)
		return sent, send

	def test_habit_reminder_window_once_and_not_when_done(self):
		h = self.habit(reminder_enabled=1, reminder_time="07:30")
		self.assertEqual(self.run_at(local(7, 25))[0], [])  # too early
		sent, send = self.run_at(local(7, 40))
		self.assertEqual(sent, [f"habit-{h['name']}"])
		self.assertEqual(send.call_args.args[1], "Time for Read")
		self.assertEqual(self.run_at(local(7, 45))[0], [])  # already sent today
		# another habit that is already done gets no reminder
		w = self.habit(habit_name="Water", reminder_enabled=1, reminder_time="09:00")
		habits.check_in(self.amy, w["name"])
		self.assertEqual(self.run_at(local(9, 5))[0], [])
		self.assertEqual(self.run_at(local(8, 31) + timedelta(hours=1))[0], [])  # 09:31, window over

	def test_reminder_follows_users_timezone(self):
		h = self.habit(reminder_enabled=1, reminder_time="07:30")
		# 07:35 in New York is not 07:35 in Kolkata
		self.assertEqual(self.run_at(local(7, 35, tz="America/New_York"))[0], [])
		self.assertEqual(self.run_at(local(7, 35))[0], [f"habit-{h['name']}"])

	def test_daily_reminder_counts_open_habits(self):
		self.habit()
		self.habit(habit_name="Walk")
		frappe.db.set_value(PROFILE, self.amy, {"daily_reminder_enabled": 1, "daily_reminder_time": "20:00:00"})
		sent, send = self.run_at(local(20, 10))
		self.assertEqual(sent, ["daily"])
		self.assertEqual(send.call_args.args[1], "2 habits left today")

	def test_daily_reminder_skipped_when_all_done_or_disabled(self):
		h = self.habit()
		frappe.db.set_value(PROFILE, self.amy, {"daily_reminder_enabled": 1, "daily_reminder_time": "20:00:00"})
		habits.check_in(self.amy, h["name"])
		self.assertEqual(self.run_at(local(20, 5))[0], [])
		habits.undo_check_in(self.amy, h["name"])
		frappe.db.set_value(PROFILE, self.amy, "daily_reminder_enabled", 0)
		self.assertEqual(self.run_at(local(20, 6))[0], [])

	def test_challenge_nudge(self):
		code = frappe.db.get_value("Atomic Challenge", {"code": "read_21"})
		challenges.join(self.amy, code)
		sent, send = self.run_at(local(19, 2))
		self.assertEqual(sent, ["challenge"])
		self.assertIn("Day 1 of 21", send.call_args.args[1])

	def test_weekly_summary_on_its_day(self):
		weekday = datetime.now(ZoneInfo(TZ)).strftime("%A")
		frappe.db.set_single_value(SETTINGS, "weekly_summary_day", weekday)
		frappe.db.set_value(PROFILE, self.amy, "weekly_summary_enabled", 1)
		self.assertEqual(self.run_at(local(17, 59))[0], [])
		sent, send = self.run_at(local(18, 3))
		self.assertEqual(sent, ["weekly"])
		self.assertEqual(send.call_args.kwargs["kind"], "summary")

	def test_run_only_touches_subscribed_users(self):
		push.subscribe(self.amy, sub("a"))
		# run() commits per user in production; here that would commit the test's own data
		with patch.object(reminders, "process_user") as process, patch("frappe.db.commit"), patch("frappe.db.rollback"):
			reminders.run(local(10, 0))
		users = {c.args[0] for c in process.call_args_list}
		self.assertIn(self.amy, users)
		self.assertNotIn(self.ben, users)

	# ------------------------------------------------------------- milestones
	def test_badge_is_pushed_after_commit(self):
		h = self.habit()
		with patch("frappe.enqueue") as enqueue:
			habits.check_in(self.amy, h["name"])
		titles = [c.kwargs["title"] for c in enqueue.call_args_list if c.args[0] == "atomic_streak.services.push.send_milestone"]
		self.assertEqual(titles, ["New badge: First Step"])
		self.assertTrue(all(c.kwargs["enqueue_after_commit"] for c in enqueue.call_args_list))

	def test_milestone_respects_preference(self):
		frappe.db.set_value(PROFILE, self.amy, "milestone_notifications", 0)
		with patch.object(push, "send") as send:
			push.send_milestone(self.amy, "New badge", "x")
		send.assert_not_called()

	# ------------------------------------------------------------- offline sync conflicts
	def test_offline_check_in_loses_to_newer_change_on_another_device(self):
		h = self.habit(daily_target=8, target_unit="glasses")
		queued = (datetime.now(timezone.utc) - timedelta(minutes=10)).timestamp() * 1000
		habits.check_in(self.amy, h["name"], value=5)  # made on another device, after the queue
		r = habits.check_in(self.amy, h["name"], value=2, client_id=str(uuid4()), source="Offline", queued_at=queued)
		self.assertTrue(r.get("conflict"))
		self.assertEqual(r["completion"]["value"], 5)
		# queued after the server change: the queued value applies
		later = (datetime.now(timezone.utc) + timedelta(seconds=30)).timestamp() * 1000
		r = habits.check_in(self.amy, h["name"], value=7, client_id=str(uuid4()), source="Offline", queued_at=later)
		self.assertFalse(r.get("conflict"))
		self.assertEqual(r["completion"]["value"], 7)

	def test_offline_undo_does_not_delete_a_newer_check_in(self):
		h = self.habit()
		queued = (datetime.now(timezone.utc) - timedelta(minutes=10)).timestamp() * 1000
		habits.check_in(self.amy, h["name"])
		r = habits.undo_check_in(self.amy, h["name"], queued_at=queued)
		self.assertTrue(r.get("conflict"))
		self.assertTrue(frappe.db.exists(COMPLETION, {"habit": h["name"]}))

	def test_resend_with_same_client_id_is_a_no_op(self):
		h = self.habit()
		q, cid = datetime.now(timezone.utc).timestamp() * 1000, str(uuid4())
		habits.check_in(self.amy, h["name"], client_id=cid, source="Offline", queued_at=q)
		habits.check_in(self.amy, h["name"], client_id=cid, source="Offline", queued_at=q)
		self.assertEqual(frappe.db.count(COMPLETION, {"habit": h["name"]}), 1)
		self.assertEqual(frappe.db.get_value(COMPLETION, {"habit": h["name"]}, "source"), "Offline")
