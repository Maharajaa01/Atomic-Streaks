"""Habit stacking (routines) endpoints (signed-in app user, own routines only)."""

import frappe

from atomic_streak.api.habit import _data, _user
from atomic_streak.services import routines
from atomic_streak.rate_limits import per_user


@frappe.whitelist(methods=["GET"])
def get_routines() -> list[dict]:
	return routines.list_routines(_user())


@frappe.whitelist(methods=["POST"])
@per_user(120)
def save_routine(data, name: str | None = None) -> dict:
	return routines.save(_user(), _data(data), name or None)


@frappe.whitelist(methods=["POST"])
@per_user(60)
def delete_routine(name: str) -> dict:
	routines.delete(_user(), name)
	return {"ok": True}
