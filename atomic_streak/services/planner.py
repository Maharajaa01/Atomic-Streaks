"""Day planner: a to-do list per date.

Tasks belong to one calendar day (in the user's own timezone). Plan tomorrow tonight, or any
day ahead; a task simply shows up when its day arrives. Unfinished tasks are never moved
silently: on today's list they are offered as "unfinished from earlier" to carry over.
"""

from datetime import date, timedelta

import frappe
from frappe import _

from atomic_streak.constants import PLAN_TASK
from atomic_streak.utils import user_today

FIELDS = ("title", "notes", "start_time", "priority")
OUT_FIELDS = ["name", "plan_date", "title", "notes", "start_time", "priority", "is_done", "done_at", "sort_order", "creation"]
MAX_PER_DAY = 100
DAYS_AHEAD = 730  # how far ahead a task can be planned
DAYS_BACK = 30  # how far back a task can be added/moved, and how far back carry-over looks
UPCOMING_DAYS = 90
MAX_MOVE = 100


def _parse_day(value, label: str = "Date") -> date:
	try:
		return frappe.utils.getdate(value) if value else None
	except Exception:
		frappe.throw(_("{0} must be a date like 2026-12-31.").format(_(label)))


def _check_range(user: str, day: date) -> None:
	today = user_today(user)
	if day < today - timedelta(days=DAYS_BACK):
		frappe.throw(_("Tasks can be planned at most {0} days in the past.").format(DAYS_BACK))
	if day > today + timedelta(days=DAYS_AHEAD):
		frappe.throw(_("Tasks can be planned at most {0} days ahead.").format(DAYS_AHEAD))


def _check_room(user: str, day: date, adding: int = 1) -> None:
	if frappe.db.count(PLAN_TASK, {"user": user, "plan_date": day}) + adding > MAX_PER_DAY:
		frappe.throw(_("A day can hold up to {0} tasks.").format(MAX_PER_DAY))


def _owned(user: str, name: str):
	if not name or frappe.db.get_value(PLAN_TASK, name, "user") != user:
		frappe.throw(_("Task not found."), frappe.DoesNotExistError)
	return frappe.get_doc(PLAN_TASK, name)


def _sort_key(t) -> tuple:
	# timed tasks first, in time order; then untimed ones in the order they were added
	return (0 if t.get("start_time") else 1, t.get("start_time") or "", t.get("sort_order") or 0, str(t.get("creation")))


def serialize(t) -> dict:
	return {
		"name": t.get("name"),
		"plan_date": str(t.get("plan_date")),
		"title": t.get("title"),
		"notes": t.get("notes") or "",
		"start_time": t.get("start_time") or None,
		"priority": t.get("priority") or "Normal",
		"is_done": 1 if t.get("is_done") else 0,
		"done_at": str(t.get("done_at")) if t.get("done_at") else None,
	}


def _tasks(filters: dict) -> list[dict]:
	rows = frappe.get_all(PLAN_TASK, filters=filters, fields=OUT_FIELDS, limit_page_length=MAX_PER_DAY * 2)
	return [serialize(t) for t in sorted(rows, key=_sort_key)]


def get_day(user: str, day=None) -> dict:
	today = user_today(user)
	day = _parse_day(day) or today
	out = {
		"date": str(day),
		"today": str(today),
		"tasks": _tasks({"user": user, "plan_date": day}),
		"carryover": [],
	}
	if day == today:
		rows = frappe.get_all(
			PLAN_TASK,
			filters={"user": user, "is_done": 0, "plan_date": ["between", [today - timedelta(days=DAYS_BACK), today - timedelta(days=1)]]},
			fields=OUT_FIELDS,
			order_by="plan_date asc, creation asc",
			limit_page_length=MAX_MOVE,
		)
		out["carryover"] = [serialize(t) for t in rows]
	out["upcoming"] = upcoming(user, today)
	return out


def upcoming(user: str, today: date | None = None) -> list[dict]:
	"""Future days (after today) that already have tasks, with done/total counts."""
	today = today or user_today(user)
	rows = frappe.db.sql(
		f"""select plan_date, count(*) as total, sum(is_done) as done
		from `tab{PLAN_TASK}`
		where user = %(user)s and plan_date > %(today)s and plan_date <= %(until)s
		group by plan_date order by plan_date asc limit 30""",
		{"user": user, "today": today, "until": today + timedelta(days=UPCOMING_DAYS)},
		as_dict=True,
	)
	return [{"date": str(r.plan_date), "total": int(r.total), "done": int(r.done or 0)} for r in rows]


def save(user: str, data: dict, name: str | None = None) -> dict:
	doc = _owned(user, name) if name else frappe.new_doc(PLAN_TASK)
	doc.user = user
	for f in FIELDS:
		if f in data:
			doc.set(f, data[f])
	if "plan_date" in data or doc.is_new():
		new_day = _parse_day(data.get("plan_date")) or user_today(user)
		if doc.is_new() or str(new_day) != str(doc.plan_date):
			_check_range(user, new_day)
			_check_room(user, new_day)
			doc.plan_date = new_day
	if "is_done" in data:
		doc.is_done = 1 if data["is_done"] else 0
	if doc.is_new():
		doc.sort_order = (frappe.db.count(PLAN_TASK, {"user": user, "plan_date": doc.plan_date}) or 0) + 1
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)
	return serialize(doc.as_dict())


def set_done(user: str, name: str, done: bool) -> dict:
	doc = _owned(user, name)
	doc.is_done = 1 if done else 0
	doc.save(ignore_permissions=True)
	return serialize(doc.as_dict())


def move(user: str, names: list, day) -> dict:
	if not isinstance(names, list) or not names:
		frappe.throw(_("Pick at least one task to move."))
	if len(names) > MAX_MOVE:
		frappe.throw(_("You can move up to {0} tasks at once.").format(MAX_MOVE))
	target = _parse_day(day)
	if not target:
		frappe.throw(_("Pick a date to move to."))
	_check_range(user, target)
	docs = [_owned(user, n) for n in dict.fromkeys(names)]
	moving = [d for d in docs if str(d.plan_date) != str(target)]
	_check_room(user, target, len(moving))
	base = frappe.db.count(PLAN_TASK, {"user": user, "plan_date": target}) or 0
	for i, d in enumerate(moving, start=1):
		d.plan_date = target
		d.sort_order = base + i
		d.save(ignore_permissions=True)
	return {"moved": len(moving), "date": str(target)}


def delete(user: str, name: str) -> None:
	_owned(user, name)
	frappe.delete_doc(PLAN_TASK, name, ignore_permissions=True)
