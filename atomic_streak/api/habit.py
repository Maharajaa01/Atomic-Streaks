"""Habit endpoints for the /atomic-streak app.

Every method requires a signed-in app user and acts only on that user's own records
(services.habits checks ownership on every read and write; controllers check it again).
"""

import frappe

from atomic_streak.services import habits
from atomic_streak.services.accounts import has_access
from atomic_streak.utils import require_login
from atomic_streak.rate_limits import per_user


def _user() -> str:
	user = require_login()
	if not has_access(user):
		raise frappe.PermissionError(frappe._("Join Atomic Streak to use this."))
	return user


def _data(data) -> dict:
	data = frappe.parse_json(data) if data else {}
	if not isinstance(data, dict):
		frappe.throw(frappe._("Invalid data."))
	return data


@frappe.whitelist(methods=["GET"])
def get_habits(status: str | None = None) -> list[dict]:
	return habits.list_habits(_user(), status)


@frappe.whitelist(methods=["GET"])
def get_habit(name: str) -> dict:
	return habits.get_habit(name, _user())


@frappe.whitelist(methods=["GET"])
def get_today_habits(date: str | None = None) -> dict:
	return habits.today_view(_user(), date)


@frappe.whitelist(methods=["POST"])
@per_user(60)
def create_habit(data) -> dict:
	return habits.create(_user(), _data(data))


@frappe.whitelist(methods=["POST"])
@per_user(300)
def update_habit(name: str, data) -> dict:
	return habits.update(_user(), name, _data(data))


@frappe.whitelist(methods=["POST"])
@per_user(120)
def set_habit_status(name: str, status: str) -> dict:
	return habits.set_status(_user(), name, status)


@frappe.whitelist(methods=["POST"])
@per_user(60)
def delete_habit(name: str) -> dict:
	habits.delete(_user(), name)
	return {"ok": True}


@frappe.whitelist(methods=["POST"])
@per_user(120)
def reorder_habits(names) -> dict:
	habits.reorder(_user(), frappe.parse_json(names) if isinstance(names, str) else names)
	return {"ok": True}


@frappe.whitelist(methods=["POST"])
@per_user(1000)
def complete_habit(
	habit: str, date: str | None = None, value=None, client_id: str | None = None, source: str = "App", queued_at=None
) -> dict:
	return habits.check_in(_user(), habit, date, value, client_id, source, queued_at)


@frappe.whitelist(methods=["POST"])
@per_user(1000)
def uncomplete_habit(habit: str, date: str | None = None, queued_at=None) -> dict:
	return habits.undo_check_in(_user(), habit, date, queued_at)


@frappe.whitelist(methods=["GET"])
def get_categories() -> list[dict]:
	return habits.list_categories(_user())


@frappe.whitelist(methods=["POST"])
@per_user(30)
def create_category(label: str, icon: str | None = None, color: str | None = None) -> dict:
	return habits.create_category(_user(), label, icon, color)


@frappe.whitelist(methods=["POST"])
@per_user(60)
def delete_category(name: str) -> dict:
	habits.delete_category(_user(), name)
	return {"ok": True}
