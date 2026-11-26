"""Phase 6 tests: XP and levels, achievements, challenges, routines and the coach.

Run:  CI=1 bench --site <site> run-tests --module atomic_streak.tests.test_gamification
"""

from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from atomic_streak.constants import CHALLENGE, CONVERSATION, PARTICIPATION, PROFILE, USER_ACHIEVEMENT, ParticipationStatus
from atomic_streak.services import accounts, challenges, gamification, habits, routines, xp
from atomic_streak.services.coach import providers, service
from atomic_streak.utils import user_today

DOMAIN = "atomicstreak.test"
PASSWORD = "Lantern-Orbit-93!"


def ch(code: str) -> str:
	"""Built-in challenges are named by hash; their stable handle is `code`."""
	return frappe.db.get_value(CHALLENGE, {"code": code})


class TestGamification(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.db.set_single_value("Atomic Streak Settings", "allow_signup", 1)
		cls.n = 0

	def setUp(self):
		# fresh users per test: rewards are cumulative, so shared users would leak state
		frappe.set_user("Administrator")
		type(self).n += 1
		self.cat = accounts.create_account("Cat Game", f"cat.g{self.n}@{DOMAIN}", PASSWORD, "Asia/Kolkata")
		self.dan = accounts.create_account("Dan Game", f"dan.g{self.n}@{DOMAIN}", PASSWORD, "Asia/Kolkata")
		frappe.set_user(self.cat)
		self.today = user_today(self.cat)

	def tearDown(self):
		frappe.set_user("Administrator")

	def habit(self, user=None, **kw):
		user = user or self.cat
		frappe.set_user(user)
		try:
			return habits.create(user, {"habit_name": "Read", "start_date": str(self.today - timedelta(days=20)), **kw})
		finally:
			frappe.set_user(self.cat)

	def profile_xp(self, user=None):
		return frappe.db.get_value(PROFILE, user or self.cat, "xp")

	# ------------------------------------------------------------------ XP
	def test_level_curve(self):
		self.assertEqual([xp.level_for(v) for v in (0, 99, 100, 299, 300, 600, 1000)], [1, 1, 2, 2, 3, 4, 5])
		p = xp.level_progress(150)
		self.assertEqual((p["level"], p["level_start"], p["next_level_at"], p["progress"]), (2, 100, 300, 25))

	def test_check_in_xp_follows_difficulty_and_undo_removes_it(self):
		h = self.habit(difficulty="Hard")
		habits.check_in(self.cat, h["name"])
		base = self.profile_xp()
		# 20 for a Hard check-in + 20 for the "First Step" achievement
		self.assertEqual(base, 40)
		habits.undo_check_in(self.cat, h["name"])
		# the check-in XP goes; the achievement, once earned, stays
		self.assertEqual(self.profile_xp(), 20)

	def test_partial_check_in_earns_nothing(self):
		h = self.habit(daily_target=10, target_unit="pages")
		habits.check_in(self.cat, h["name"], value=3)
		self.assertEqual(frappe.db.get_value("Atomic Habit Completion", {"habit": h["name"]}, "xp_awarded"), 0)

	# ------------------------------------------------------------ achievements
	def test_achievement_earned_once_and_celebrated_once(self):
		h = self.habit()
		habits.check_in(self.cat, h["name"], self.today - timedelta(days=1))
		habits.check_in(self.cat, h["name"])
		self.assertEqual(frappe.db.count(USER_ACHIEVEMENT, {"user": self.cat, "achievement": "first_completion"}), 1)
		pending = gamification.pending_celebrations(self.cat)["achievements"]
		self.assertEqual([a["code"] for a in pending], ["first_completion"])
		# another user cannot mark it seen
		gamification.mark_celebrated(self.dan, [pending[0]["name"]], [])
		self.assertEqual(len(gamification.pending_celebrations(self.cat)["achievements"]), 1)
		gamification.mark_celebrated(self.cat, [pending[0]["name"]], [])
		self.assertEqual(gamification.pending_celebrations(self.cat)["achievements"], [])

	def test_streak_achievement(self):
		h = self.habit()
		for n in (2, 1, 0):
			habits.check_in(self.cat, h["name"], self.today - timedelta(days=n))
		earned = set(frappe.get_all(USER_ACHIEVEMENT, filters={"user": self.cat}, pluck="achievement"))
		self.assertIn("streak_3", earned)
		self.assertNotIn("streak_7", earned)

	def test_summary_lists_all_badges(self):
		s = gamification.summary(self.cat)
		self.assertEqual(s["level"], 1)
		self.assertGreaterEqual(len(s["achievements"]), 8)
		self.assertTrue(all("earned" in a for a in s["achievements"]))

	# -------------------------------------------------------------- challenges
	def test_join_creates_habit_and_blocks_double_join(self):
		r = challenges.join(self.cat, ch("drink_water_7"))
		self.assertEqual(frappe.db.get_value("Atomic Habit", r["habit"], "habit_name"), "Drink 8 glasses of water")
		with self.assertRaises(frappe.ValidationError):
			challenges.join(self.cat, ch("drink_water_7"))
		mine = challenges.overview(self.cat)["mine"]
		self.assertEqual(mine[0]["progress"]["target"], 7)
		self.assertEqual(mine[0]["day"], 1)

	def backdated(self, user, habit, days=7, code="drink_water_7"):
		# joined earlier than today, so a whole challenge can be checked in within the 7-day edit window
		p = frappe.get_doc(
			{"doctype": PARTICIPATION, "user": user, "challenge": ch(code), "habit": habit, "start_date": self.today - timedelta(days=days - 1)}
		)
		p.insert(ignore_permissions=True)
		return p.name

	def test_challenge_completes_at_85_percent_and_reverts_on_undo(self):
		h = self.habit(start_date=str(self.today - timedelta(days=10)))
		name = self.backdated(self.cat, h["name"])
		for n in range(1, 7):  # 6 of 7 days
			habits.check_in(self.cat, h["name"], self.today - timedelta(days=n))
		row = frappe.db.get_value(PARTICIPATION, name, ["status", "days_completed", "xp_awarded"], as_dict=True)
		self.assertEqual((row.status, row.days_completed, row.xp_awarded), (ParticipationStatus.COMPLETED, 6, 70))
		self.assertIn("first_challenge", frappe.get_all(USER_ACHIEVEMENT, filters={"user": self.cat}, pluck="achievement"))
		self.assertEqual(len(gamification.pending_celebrations(self.cat)["challenges"]), 1)
		habits.undo_check_in(self.cat, h["name"], self.today - timedelta(days=1))
		row = frappe.db.get_value(PARTICIPATION, name, ["status", "xp_awarded", "celebrated"], as_dict=True)
		self.assertEqual((row.status, row.xp_awarded, row.celebrated), (ParticipationStatus.ACTIVE, 0, 0))

	def test_challenge_fails_when_unreachable(self):
		h = self.habit(start_date=str(self.today - timedelta(days=10)))
		name = self.backdated(self.cat, h["name"])
		challenges.recompute(name)  # 0 done, only today left: 6 needed, 1 possible
		self.assertEqual(frappe.db.get_value(PARTICIPATION, name, "status"), ParticipationStatus.FAILED)

	def test_leave_and_foreign_participation(self):
		r = challenges.join(self.cat, ch("read_21"))
		with self.assertRaises(frappe.DoesNotExistError):
			challenges.leave(self.dan, r["name"])
		challenges.leave(self.cat, r["name"])
		self.assertEqual(frappe.db.get_value(PARTICIPATION, r["name"], "status"), ParticipationStatus.ABANDONED)
		# rejoining after leaving is allowed
		challenges.join(self.cat, ch("read_21"), habit=r["habit"])

	def test_cannot_join_with_someone_elses_habit(self):
		other = self.habit(user=self.dan)
		with self.assertRaises((frappe.DoesNotExistError, frappe.PermissionError)):
			challenges.join(self.cat, ch("read_21"), habit=other["name"])

	def test_custom_challenge_reward_is_server_side_and_private(self):
		c = challenges.create_custom(self.cat, "Stretch daily", 14)
		self.assertEqual(c["xp_reward"], 140)
		self.assertEqual(challenges.create_custom(self.cat, "Long one", 100)["xp_reward"], challenges.CUSTOM_XP_MAX)
		self.assertIn(c["name"], [x["name"] for x in challenges.overview(self.cat)["discover"]])
		frappe.set_user(self.dan)
		self.assertNotIn(c["name"], [x["name"] for x in challenges.overview(self.dan)["discover"]])
		with self.assertRaises(frappe.DoesNotExistError):
			challenges.join(self.dan, c["name"])

	def test_custom_challenge_length_is_checked(self):
		with self.assertRaises(frappe.ValidationError):
			challenges.create_custom(self.cat, "Too long", 400)

	def test_app_user_cannot_edit_builtin_challenge(self):
		doc = frappe.get_doc(CHALLENGE, ch("read_21"))
		doc.xp_reward = 99999
		with self.assertRaises(frappe.PermissionError):
			doc.save(ignore_permissions=True)

	# ---------------------------------------------------------------- routines
	def test_routine_round_trip(self):
		a, b = self.habit(habit_name="Water"), self.habit(habit_name="Stretch")
		r = routines.save(self.cat, {"routine_name": "Morning", "cue": "After I wake up", "steps": [{"habit": b["name"], "note": "2 min"}, a["name"]]})
		self.assertEqual([s["habit_name"] for s in r["steps"]], ["Stretch", "Water"])
		habits.check_in(self.cat, a["name"])
		r = routines.list_routines(self.cat)[0]
		self.assertEqual((r["done_today"], r["steps"][1]["done"], r["steps"][0]["note"]), (1, True, "2 min"))
		r = routines.save(self.cat, {"steps": [a["name"]]}, r["name"])
		self.assertEqual(len(r["steps"]), 1)

	def test_routine_isolation(self):
		mine = self.habit()
		theirs = self.habit(user=self.dan)
		with self.assertRaises((frappe.PermissionError, frappe.DoesNotExistError, frappe.ValidationError)):
			routines.save(self.cat, {"routine_name": "Sneaky", "steps": [theirs["name"]]})
		r = routines.save(self.cat, {"routine_name": "Mine", "steps": [mine["name"]]})
		frappe.set_user(self.dan)
		for call in (lambda: routines.save(self.dan, {"routine_name": "x"}, r["name"]), lambda: routines.delete(self.dan, r["name"])):
			with self.assertRaises(frappe.DoesNotExistError):
				call()
		self.assertEqual(routines.list_routines(self.dan), [])

	def test_routine_rejects_duplicate_steps(self):
		h = self.habit()
		with self.assertRaises(frappe.ValidationError):
			routines.save(self.cat, {"routine_name": "Twice", "steps": [h["name"], h["name"]]})

	# ------------------------------------------------------------------- coach
	def test_rules_coach_without_ai(self):
		with patch.object(providers, "get_provider", return_value=None):
			r = service.chat(self.cat, "Suggest habits for better sleep")
		self.assertEqual(r["provider"], "rules")
		self.assertTrue(r["suggestions"])
		self.assertEqual(r["suggestions"][0]["category"], "Health")
		conv = service.get(self.cat, r["conversation"])
		self.assertEqual([m["role"] for m in conv["messages"]], ["user", "assistant"])

	def test_coach_conversations_are_private(self):
		with patch.object(providers, "get_provider", return_value=None):
			r = service.chat(self.cat, "How am I doing this week?")
		frappe.set_user(self.dan)
		for call in (
			lambda: service.get(self.dan, r["conversation"]),
			lambda: service.chat(self.dan, "hi", r["conversation"]),
			lambda: service.delete(self.dan, r["conversation"]),
		):
			with self.assertRaises(frappe.DoesNotExistError):
				call()
		self.assertEqual(service.list_conversations(self.dan), [])

	def test_ai_reply_and_fallback(self):
		class Good:
			def reply(self, history, context_text):
				assert history[-1] == {"role": "user", "content": "Help me read more"}
				assert "Habits" in context_text or "No habits" in context_text
				return {"text": "Try two pages after dinner.", "provider": "claude-opus-5-5"}

		class Down:
			def reply(self, history, context_text):
				raise providers.ProviderUnavailable("network")

		with patch.object(providers, "get_provider", return_value=Good()):
			r = service.chat(self.cat, "Help me read more")
		self.assertEqual((r["reply"], r["provider"], r["note"]), ("Try two pages after dinner.", "claude-opus-5-5", None))
		self.assertTrue(r["suggestions"])  # catalogue cards still come with an AI answer
		with patch.object(providers, "get_provider", return_value=Down()):
			r2 = service.chat(self.cat, "Help me read more", r["conversation"])
		self.assertEqual(r2["provider"], "rules")
		self.assertTrue(r2["note"])
		self.assertEqual(len(service.get(self.cat, r["conversation"])["messages"]), 4)

	def test_ai_daily_limit(self):
		class Good:
			def reply(self, history, context_text):
				return {"text": "ok", "provider": "claude-opus-5-5"}

		frappe.db.set_single_value("Atomic Streak Settings", "ai_daily_message_limit", 1)
		frappe.clear_document_cache("Atomic Streak Settings", "Atomic Streak Settings")
		try:
			with patch.object(providers, "get_provider", return_value=Good()):
				first = service.chat(self.cat, "hello")
				second = service.chat(self.cat, "hello again", first["conversation"])
		finally:
			frappe.db.set_single_value("Atomic Streak Settings", "ai_daily_message_limit", 30)
			frappe.clear_document_cache("Atomic Streak Settings", "Atomic Streak Settings")
		self.assertEqual(first["provider"], "claude-opus-5-5")
		self.assertEqual(second["provider"], "rules")
		self.assertTrue(second["note"])

	def test_coach_rejects_empty_and_oversized_messages(self):
		for msg in ("", "   ", "x" * (service.MAX_MESSAGE + 1)):
			with self.assertRaises(frappe.ValidationError):
				service.chat(self.cat, msg)
		self.assertEqual(frappe.db.count(CONVERSATION, {"user": self.cat}), 0)
