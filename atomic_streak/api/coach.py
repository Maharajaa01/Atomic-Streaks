"""AI habit coach endpoints (signed-in app user, own conversations only)."""

import frappe

from atomic_streak.api.habit import _user
from atomic_streak.services.coach import service
from atomic_streak.rate_limits import per_user


@frappe.whitelist(methods=["GET"])
def get_status() -> dict:
	_user()
	return service.ai_status()


@frappe.whitelist(methods=["POST"])
@per_user(60)
def chat(message: str, conversation: str | None = None) -> dict:
	return service.chat(_user(), message, conversation or None)


@frappe.whitelist(methods=["GET"])
def get_conversations() -> list[dict]:
	return service.list_conversations(_user())


@frappe.whitelist(methods=["GET"])
def get_conversation(name: str) -> dict:
	return service.get(_user(), name)


@frappe.whitelist(methods=["POST"])
@per_user(60)
def delete_conversation(name: str) -> dict:
	service.delete(_user(), name)
	return {"ok": True}


@frappe.whitelist(methods=["GET"])
def get_weekly_summary() -> dict:
	return service.weekly_summary(_user())


@frappe.whitelist(methods=["GET"])
def suggest_habits(goal: str | None = None) -> list[dict]:
	_user()
	return service.suggestions_for(goal)
