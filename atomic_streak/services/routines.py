"""Habit stacking: ordered routines ("After I wake up: water, meditate, read")."""

import frappe
from frappe import _

from atomic_streak.constants import COMPLETION, HABIT, ROUTINE, CompletionStatus
from atomic_streak.utils import user_today

FIELDS = ("routine_name", "cue", "icon", "color", "time_of_day", "is_active")
MAX_ROUTINES = 30


def _owned(user: str, name: str):
	if not name or frappe.db.get_value(ROUTINE, name, "user") != user:
		frappe.throw(_("Routine not found."), frappe.DoesNotExistError)
	return frappe.get_doc(ROUTINE, name)


def serialize(doc, user: str) -> dict:
	today = user_today(user)
	names = [i.habit for i in doc.items]
	info = {h.name: h for h in frappe.get_all(HABIT, filters={"name": ["in", names or [""]]}, fields=["name", "habit_name", "icon", "color", "status", "habit_type", "daily_target", "target_unit", "current_streak"])}
	done = {
		c.habit: c.status
		for c in frappe.get_all(COMPLETION, filters={"user": user, "habit": ["in", names or [""]], "completion_date": today}, fields=["habit", "status"])
	}
	steps = []
	for i in doc.items:
		h = info.get(i.habit)
		if not h:
			continue
		steps.append({"habit": h.name, "habit_name": h.habit_name, "icon": h.icon, "color": h.color, "status": h.status, "habit_type": h.habit_type,
					  "daily_target": h.daily_target, "target_unit": h.target_unit, "current_streak": h.current_streak,
					  "note": i.cue_note, "done": done.get(h.name) == CompletionStatus.COMPLETED})
	return {
		"name": doc.name,
		**{f: doc.get(f) for f in FIELDS},
		"sort_order": doc.sort_order,
		"steps": steps,
		"done_today": sum(1 for s in steps if s["done"]),
	}


def list_routines(user: str) -> list[dict]:
	return [serialize(frappe.get_doc(ROUTINE, n), user) for n in frappe.get_all(ROUTINE, filters={"user": user}, pluck="name", order_by="sort_order asc, creation asc")]


def save(user: str, data: dict, name: str | None = None) -> dict:
	if not name and frappe.db.count(ROUTINE, {"user": user}) >= MAX_ROUTINES:
		frappe.throw(_("You can have up to {0} routines.").format(MAX_ROUTINES))
	doc = _owned(user, name) if name else frappe.new_doc(ROUTINE)
	doc.user = user
	for f in FIELDS:
		if f in data:
			doc.set(f, data[f])
	if "steps" in data:
		steps = data.get("steps") or []
		if not isinstance(steps, list):
			frappe.throw(_("Steps must be a list."))
		doc.set("items", [{"habit": s.get("habit") if isinstance(s, dict) else s, "cue_note": (s.get("note") if isinstance(s, dict) else None)} for s in steps])
	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)
	return serialize(doc, user)


def delete(user: str, name: str) -> None:
	_owned(user, name)
	frappe.delete_doc(ROUTINE, name, ignore_permissions=True)
