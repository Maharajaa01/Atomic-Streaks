"""Challenges, achievements, XP and celebrations (signed-in app user, own data only)."""

import frappe

from atomic_streak.api.habit import _user
from atomic_streak.services import challenges, gamification
from atomic_streak.rate_limits import per_user


@frappe.whitelist(methods=["GET"])
def get_challenges() -> dict:
	return challenges.overview(_user())


@frappe.whitelist(methods=["POST"])
@per_user(30)
def join_challenge(challenge: str, habit: str | None = None, habit_name: str | None = None) -> dict:
	return challenges.join(_user(), challenge, habit or None, habit_name or None)


@frappe.whitelist(methods=["POST"])
@per_user(30)
def leave_challenge(name: str) -> dict:
	challenges.leave(_user(), name)
	return {"ok": True}


@frappe.whitelist(methods=["POST"])
@per_user(20)
def create_challenge(title: str, duration_days: int, description: str | None = None, icon: str | None = None, color: str | None = None) -> dict:
	return challenges.create_custom(_user(), title, duration_days, description, icon, color)


@frappe.whitelist(methods=["GET"])
def get_progress() -> dict:
	"""Level, XP and every badge (earned or still to earn)."""
	return gamification.summary(_user())


@frappe.whitelist(methods=["GET"])
def get_celebrations() -> dict:
	return gamification.pending_celebrations(_user())


@frappe.whitelist(methods=["POST"])
@per_user(300)
def mark_celebrated(achievements=None, challenges_done=None) -> dict:
	gamification.mark_celebrated(_user(), frappe.parse_json(achievements) or [], frappe.parse_json(challenges_done) or [])
	return {"ok": True}
