"""Habit management and daily check-ins for the signed-in user.

Every function takes the acting user explicitly and only ever touches that user's rows; the
API layer passes frappe.session.user. Writes go through the DocType controllers, so all
validation (ownership, dates, targets, uniqueness) and streak recalculation apply.
"""

from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from atomic_streak.constants import (
	CATEGORY,
	COMPLETION,
	HABIT,
	PROFILE,
	WEEKDAYS,
	CompletionStatus,
	HabitStatus,
	HabitType,
)
from atomic_streak.services.schedule import Schedule
from atomic_streak.services.xp import level_progress
from atomic_streak.utils import user_today

# Fields a user may set through the API. Anything else in the payload is ignored, so
# calculated fields (streaks, totals), ownership and status can't be written this way.
EDITABLE = (
	"habit_name",
	"description",
	"icon",
	"category",
	"color",
	"habit_type",
	"frequency",
	"interval_days",
	"start_date",
	"end_date",
	"time_of_day",
	"preferred_time",
	"daily_target",
	"target_unit",
	"difficulty",
	"reminder_enabled",
	"reminder_time",
	"notes",
)
LIST_FIELDS = (
	"name",
	*EDITABLE,
	"status",
	"sort_order",
	"current_streak",
	"longest_streak",
	"total_completions",
	"last_completed_on",
	"creation",
)
TIME_ORDER = {"Morning": 0, "Afternoon": 1, "Evening": 2, "Night": 3, "Anytime": 4}
MAX_HABITS = 200


# ------------------------------------------------------------------ helpers
def get_owned(name: str, user: str):
	"""The habit if it belongs to `user`; the same 'not found' otherwise (no probing)."""
	if not name or not isinstance(name, str) or frappe.db.get_value(HABIT, name, "user") != user:
		frappe.throw(_("Habit not found."), frappe.DoesNotExistError)
	return frappe.get_doc(HABIT, name)


def _weekdays_for(names: list[str]) -> dict[str, list[str]]:
	out: dict[str, list[str]] = {n: [] for n in names}
	if names:
		for row in frappe.get_all(
			"Atomic Habit Schedule",
			filters={"parenttype": HABIT, "parent": ["in", names]},
			fields=["parent", "weekday"],
			order_by="idx asc",
		):
			out[row.parent].append(row.weekday)
	return out


def _pauses_for(names: list[str]) -> dict[str, list]:
	out: dict[str, list] = {n: [] for n in names}
	if names:
		for row in frappe.get_all(
			"Atomic Habit Pause",
			filters={"parenttype": HABIT, "parent": ["in", names]},
			fields=["parent", "from_date", "to_date"],
		):
			out[row.parent].append(row)
	return out


def schedules_for(rows) -> dict[str, Schedule]:
	"""Schedules (weekdays + pause periods) for many habit rows in three queries."""
	names = [r.name for r in rows]
	weekdays, pauses = _weekdays_for(names), _pauses_for(names)
	return {r.name: Schedule(r, weekdays[r.name], pauses[r.name]) for r in rows}


def _categories() -> dict[str, dict]:
	return {
		c.name: c
		for c in frappe.get_all(CATEGORY, fields=["name", "category_name", "icon", "color", "is_standard", "user"])
	}


def serialize(row, weekdays: list[str], categories: dict) -> dict:
	cat = categories.get(row.get("category")) if row.get("category") else None
	data = {f: row.get(f) for f in LIST_FIELDS}
	data["weekdays"] = weekdays
	data["category_info"] = (
		{"name": cat.name, "label": cat.category_name, "icon": cat.icon, "color": cat.color} if cat else None
	)
	for f in ("start_date", "end_date", "last_completed_on"):
		data[f] = str(data[f]) if data[f] else None
	data["creation"] = str(data["creation"]) if data.get("creation") else None
	return data


def _apply(doc, data: dict) -> None:
	for field in EDITABLE:
		if field in data:
			doc.set(field, data[field])
	if "weekdays" in data:
		days = data.get("weekdays") or []
		if not isinstance(days, list):
			frappe.throw(_("Weekdays must be a list."))
		doc.set("schedule", [{"weekday": d} for d in days if d in WEEKDAYS])


# ------------------------------------------------------------------ reads
def list_habits(user: str, status: str | None = None) -> list[dict]:
	filters: dict = {"user": user}
	if status == "archived":
		filters["status"] = HabitStatus.ARCHIVED
	elif status != "all":
		filters["status"] = ["!=", HabitStatus.ARCHIVED]
	rows = frappe.get_all(HABIT, filters=filters, fields=list(LIST_FIELDS), order_by="sort_order asc, creation asc")
	weekdays = _weekdays_for([r.name for r in rows])
	cats = _categories()
	return [serialize(r, weekdays[r.name], cats) for r in rows]


def get_habit(name: str, user: str) -> dict:
	doc = get_owned(name, user)
	return serialize(doc.as_dict(), [r.weekday for r in doc.schedule], _categories())


def today_view(user: str, day: date | None = None) -> dict:
	"""Habits due on `day` (default: the user's today) with their check-ins, plus summaries."""
	today = user_today(user)
	day = getdate(day) if day else today
	if day > today:
		frappe.throw(_("You can't look ahead past today."))

	rows = frappe.get_all(
		HABIT,
		filters={"user": user, "status": ["in", [HabitStatus.ACTIVE, HabitStatus.COMPLETED]]},
		fields=list(LIST_FIELDS),
	)
	weekdays = _weekdays_for([r.name for r in rows])
	schedules = schedules_for(rows)
	done = {
		c.habit: c
		for c in frappe.get_all(
			COMPLETION,
			filters={"user": user, "completion_date": day},
			fields=["name", "habit", "value", "target", "status"],
		)
	}
	cats = _categories()
	items = []
	for r in rows:
		if not schedules[r.name].is_scheduled(day):
			continue
		if r.status == HabitStatus.COMPLETED and r.name not in done:
			continue  # a finished one-time goal only shows on the day it was finished
		item = serialize(r, weekdays[r.name], cats)
		c = done.get(r.name)
		item["completion"] = (
			{"name": c.name, "value": flt(c.value), "target": flt(c.target), "status": c.status} if c else None
		)
		items.append(item)
	items.sort(key=lambda h: (TIME_ORDER.get(h["time_of_day"] or "Anytime", 4), h["preferred_time"] or "99", h["sort_order"] or 0))

	completed = sum(1 for h in items if h["completion"] and h["completion"]["status"] == CompletionStatus.COMPLETED)
	profile = frappe.db.get_value(
		PROFILE, user, ["current_streak", "longest_streak", "total_completions", "xp", "level", "week_starts_on"], as_dict=True
	) or frappe._dict(current_streak=0, longest_streak=0, total_completions=0, xp=0, level=1, week_starts_on="Monday")
	return {
		"date": str(day),
		"today": str(today),
		"habits": items,
		"summary": {
			"total": len(items),
			"completed": completed,
			"remaining": len(items) - completed,
			"percent": round(100 * completed / len(items)) if items else 0,
			"active_habits": frappe.db.count(HABIT, {"user": user, "status": HabitStatus.ACTIVE}),
		},
		"streak": {
			"current": cint(profile.current_streak),
			"longest": cint(profile.longest_streak),
			"total_completions": cint(profile.total_completions),
		},
		"xp": cint(profile.xp),
		"level": cint(profile.level) or 1,
		"level_progress": level_progress(cint(profile.xp)),
		"week": week_progress(user, today, profile.week_starts_on or "Monday"),
	}


def week_progress(user: str, today: date, week_starts_on: str = "Monday") -> list[dict]:
	"""Scheduled vs completed for each day of the current week (future days are empty)."""
	start_idx = 6 if week_starts_on == "Sunday" else 0
	start = today - timedelta(days=(today.weekday() - start_idx) % 7)
	days = [start + timedelta(days=i) for i in range(7)]
	rows = frappe.get_all(
		HABIT,
		# every status: pause periods already exclude the days a habit was paused or archived
		filters={"user": user, "habit_type": ["!=", HabitType.ONE_TIME]},
		fields=["name", "frequency", "habit_type", "start_date", "end_date", "interval_days"],
	)
	schedules = schedules_for(rows)
	done: dict[date, set[str]] = {}
	for c in frappe.get_all(
		COMPLETION,
		filters={"user": user, "completion_date": ["between", [days[0], days[-1]]], "status": CompletionStatus.COMPLETED},
		fields=["habit", "completion_date"],
	):
		done.setdefault(getdate(c.completion_date), set()).add(c.habit)
	out = []
	for d in days:
		due = [n for n, s in schedules.items() if s.is_scheduled(d)] if d <= today else []
		hit = len([n for n in due if n in done.get(d, set())])
		out.append(
			{
				"date": str(d),
				"weekday": WEEKDAYS[d.weekday()][:3],
				"scheduled": len(due),
				"completed": hit,
				"percent": round(100 * hit / len(due)) if due else 0,
				"is_today": d == today,
				"is_future": d > today,
			}
		)
	return out


# ------------------------------------------------------------------ writes
def create(user: str, data: dict) -> dict:
	if frappe.db.count(HABIT, {"user": user}) >= MAX_HABITS:
		frappe.throw(_("You can have up to {0} habits.").format(MAX_HABITS))
	doc = frappe.new_doc(HABIT)
	doc.user = user
	_apply(doc, data)
	doc.sort_order = cint(
		frappe.db.sql(f"select coalesce(max(sort_order), 0) from `tab{HABIT}` where user = %s", user)[0][0]
	) + 1
	doc.insert(ignore_permissions=True)
	return get_habit(doc.name, user)


def update(user: str, name: str, data: dict) -> dict:
	doc = get_owned(name, user)
	_apply(doc, data)
	doc.save(ignore_permissions=True)
	return get_habit(doc.name, user)


def set_status(user: str, name: str, status: str) -> dict:
	if status not in (HabitStatus.ACTIVE, HabitStatus.PAUSED, HabitStatus.ARCHIVED):
		frappe.throw(_("Unknown status."))
	doc = get_owned(name, user)
	doc.status = status
	doc.save(ignore_permissions=True)
	return get_habit(doc.name, user)


def delete(user: str, name: str) -> None:
	get_owned(name, user)
	frappe.delete_doc(HABIT, name, ignore_permissions=True)


def reorder(user: str, names: list[str]) -> None:
	if not isinstance(names, list) or len(names) > MAX_HABITS:
		frappe.throw(_("Invalid order."))
	owned = set(frappe.get_all(HABIT, filters={"user": user, "name": ["in", names or [""]]}, pluck="name"))
	for i, name in enumerate(n for n in names if n in owned):
		frappe.db.set_value(HABIT, name, "sort_order", i + 1, update_modified=False)


def _newer_than_queue(completion_modified, queued_at) -> bool:
	"""True when the stored check-in changed after an offline action was queued.

	`queued_at` is the browser's clock in epoch milliseconds. Server times are naive in the
	system timezone. A few seconds of clock skew are allowed in favour of the queued action.
	"""
	if not queued_at or not completion_modified:
		return False
	from datetime import datetime, timezone
	from zoneinfo import ZoneInfo

	try:
		queued = datetime.fromtimestamp(flt(queued_at) / 1000, tz=timezone.utc)
	except (OverflowError, OSError, ValueError):
		return False
	stored = completion_modified.replace(tzinfo=ZoneInfo(frappe.utils.get_system_timezone()))
	return (stored - queued).total_seconds() > 5


def check_in(
	user: str, habit: str, day=None, value=None, client_id: str | None = None, source: str = "App", queued_at=None
) -> dict:
	"""Record (or update) the check-in for `habit` on `day`. Safe to repeat.

	* Same client_id again -> the stored check-in is returned unchanged (offline re-sends).
	* A check-in already exists for that day -> its value is updated, never duplicated.
	* `value` is the day's total (e.g. 5 of 8 glasses); omitted means "fully done".
	* `queued_at` (offline sync): if the day's check-in was changed on another device after this
	  action was queued, the newer server value wins and the response says `conflict: true`.
	"""
	doc = get_owned(habit, user)
	day = getdate(day) if day else user_today(user)
	if client_id:
		existing = frappe.db.get_value(COMPLETION, {"client_id": client_id}, ["name", "user"], as_dict=True)
		if existing:
			if existing.user != user:
				frappe.throw(_("Invalid client id."))
			return result(user, doc.name, day)

	value = doc.daily_target if value in (None, "") else flt(value)
	name = frappe.db.get_value(COMPLETION, {"habit": habit, "completion_date": day})
	if name:
		completion = frappe.get_doc(COMPLETION, name)
		if _newer_than_queue(completion.modified, queued_at):
			return {**result(user, habit, day), "conflict": True}
		# remember this device's id on the existing record too, so re-sending it is a no-op
		adopt_id = bool(client_id) and not completion.client_id
		if flt(completion.value) != value or adopt_id:
			completion.value = value
			if adopt_id:
				completion.client_id = client_id
			completion.save(ignore_permissions=True)
	else:
		completion = frappe.get_doc(
			{
				"doctype": COMPLETION,
				"user": user,
				"habit": habit,
				"completion_date": day,
				"value": value,
				"client_id": client_id or None,
				"source": source if source in ("App", "Offline", "Routine") else "App",
			}
		)
		try:
			completion.insert(ignore_permissions=True)
		except (frappe.UniqueValidationError, frappe.DuplicateEntryError):
			# a parallel request recorded it first; return what is stored
			frappe.clear_messages()
			return result(user, habit, day)

	if doc.habit_type == HabitType.ONE_TIME and completion.status == CompletionStatus.COMPLETED:
		frappe.db.set_value(HABIT, habit, "status", HabitStatus.COMPLETED)
	return result(user, habit, day)


def undo_check_in(user: str, habit: str, day=None, queued_at=None) -> dict:
	doc = get_owned(habit, user)
	day = getdate(day) if day else user_today(user)
	name = frappe.db.get_value(COMPLETION, {"habit": habit, "completion_date": day, "user": user})
	if name and _newer_than_queue(frappe.db.get_value(COMPLETION, name, "modified"), queued_at):
		return {**result(user, habit, day), "conflict": True}
	if name:
		frappe.delete_doc(COMPLETION, name, ignore_permissions=True)
	if doc.habit_type == HabitType.ONE_TIME and doc.status == HabitStatus.COMPLETED:
		frappe.db.set_value(HABIT, habit, "status", HabitStatus.ACTIVE)
	return result(user, habit, day)


def result(user: str, habit: str, day: date) -> dict:
	c = frappe.db.get_value(
		COMPLETION, {"habit": habit, "completion_date": day}, ["name", "value", "target", "status", "client_id"], as_dict=True
	)
	h = frappe.db.get_value(
		HABIT, habit, ["current_streak", "longest_streak", "total_completions", "last_completed_on", "status"], as_dict=True
	)
	p = frappe.db.get_value(PROFILE, user, ["current_streak", "longest_streak", "total_completions", "xp"], as_dict=True) or {}
	from atomic_streak.services import gamification, xp

	return {
		"xp": xp.level_progress(cint(p.get("xp"))),
		"celebrations": gamification.pending_celebrations(user),
		"date": str(day),
		"habit": habit,
		"completion": (
			{"name": c.name, "value": flt(c.value), "target": flt(c.target), "status": c.status, "client_id": c.client_id}
			if c
			else None
		),
		"stats": {
			"current_streak": cint(h.current_streak),
			"longest_streak": cint(h.longest_streak),
			"total_completions": cint(h.total_completions),
			"status": h.status,
		},
		"streak": {
			"current": cint(p.get("current_streak")),
			"longest": cint(p.get("longest_streak")),
			"total_completions": cint(p.get("total_completions")),
		},
	}


# ------------------------------------------------------------------ categories
def list_categories(user: str) -> list[dict]:
	return frappe.get_all(
		CATEGORY,
		filters={"is_standard": 1},
		fields=["name", "category_name as label", "icon", "color", "is_standard"],
		order_by="sort_order asc",
	) + frappe.get_all(
		CATEGORY,
		filters={"user": user, "is_standard": 0},
		fields=["name", "category_name as label", "icon", "color", "is_standard"],
		order_by="category_name asc",
	)


MAX_CATEGORIES = 50


def create_category(user: str, label: str, icon: str | None = None, color: str | None = None) -> dict:
	if frappe.db.count(CATEGORY, {"user": user}) >= MAX_CATEGORIES:
		frappe.throw(_("You can have up to {0} categories of your own.").format(MAX_CATEGORIES))
	doc = frappe.get_doc(
		{"doctype": CATEGORY, "category_name": label, "user": user, "icon": icon or "tag", "color": color or "#7657F6"}
	)
	doc.insert(ignore_permissions=True)
	return {"name": doc.name, "label": doc.category_name, "icon": doc.icon, "color": doc.color, "is_standard": 0}


def delete_category(user: str, name: str) -> None:
	if frappe.db.get_value(CATEGORY, name, "user") != user:
		frappe.throw(_("Category not found."), frappe.DoesNotExistError)
	frappe.delete_doc(CATEGORY, name, ignore_permissions=True)
