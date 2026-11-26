"""Day planner endpoints (signed-in app user, own tasks only)."""

import frappe

from atomic_streak.api.habit import _data, _user
from atomic_streak.rate_limits import per_user
from atomic_streak.services import planner


@frappe.whitelist(methods=["GET"])
def get_day(date: str | None = None) -> dict:
	return planner.get_day(_user(), date or None)


@frappe.whitelist(methods=["POST"])
@per_user(600)
def save_task(data, name: str | None = None) -> dict:
	return planner.save(_user(), _data(data), name or None)


@frappe.whitelist(methods=["POST"])
@per_user(1200)
def set_done(name: str, done=1) -> dict:
	return planner.set_done(_user(), name, str(done).strip().lower() in ("1", "true"))


@frappe.whitelist(methods=["POST"])
@per_user(120)
def move_tasks(names, date: str) -> dict:
	if isinstance(names, str):
		names = frappe.parse_json(names)
	return planner.move(_user(), names, date)


@frappe.whitelist(methods=["POST"])
@per_user(300)
def delete_task(name: str) -> dict:
	planner.delete(_user(), name)
	return {"ok": True}
