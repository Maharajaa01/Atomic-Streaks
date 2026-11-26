"""Small helpers shared by controllers, services and APIs."""

import re
from datetime import date, datetime
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

import frappe
from frappe import _

from atomic_streak.constants import PROFILE

HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
ICON_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
HH_MM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def is_admin(user: str | None = None) -> bool:
	"""Administrator and System Managers may act on any user's records (Desk, patches, jobs)."""
	user = user or frappe.session.user
	return user == "Administrator" or "System Manager" in frappe.get_roles(user)


def require_login() -> str:
	user = frappe.session.user
	if not user or user == "Guest":
		raise frappe.PermissionError(_("Please sign in to continue."))
	return user


@lru_cache(maxsize=1)
def _timezones() -> frozenset[str]:
	return frozenset(available_timezones())


def is_valid_timezone(tz: str | None) -> bool:
	return bool(tz) and tz in _timezones()


def get_user_timezone(user: str | None = None) -> str:
	"""Profile timezone, else the Frappe user's, else the site's."""
	user = user or frappe.session.user
	tz = frappe.db.get_value(PROFILE, user, "timezone") if user and user != "Guest" else None
	if not is_valid_timezone(tz):
		tz = frappe.db.get_value("User", user, "time_zone") if user else None
	if not is_valid_timezone(tz):
		tz = frappe.utils.get_system_timezone()
	return tz


def user_now(user: str | None = None) -> datetime:
	"""Aware datetime in the user's timezone."""
	try:
		zone = ZoneInfo(get_user_timezone(user))
	except ZoneInfoNotFoundError:
		zone = ZoneInfo("UTC")
	return datetime.now(zone)


def user_today(user: str | None = None) -> date:
	return user_now(user).date()


def validate_color(value: str | None, label: str) -> None:
	if value and not HEX_COLOR.match(value):
		frappe.throw(_("{0} must be a colour like #7657F6.").format(label))


def validate_icon(value: str | None) -> None:
	if value and (len(value) > 40 or not ICON_NAME.match(value)):
		frappe.throw(_("Icon must be an icon name such as 'book-open'."))


# real markup only: "<" directly followed by a letter or "/" (so "a < b" and "<3" survive)
HTML_TAG = re.compile(r"</?[A-Za-z][^<>]*>")


def clean_text(value: str | None, label: str, max_len: int, required: bool = False) -> str:
	"""Plain text only: user text is shown in the app, in push notifications and in Desk, so
	markup is removed here rather than trusted to every place that displays it."""
	text = HTML_TAG.sub("", value or "").strip()
	if required and not text:
		frappe.throw(_("{0} is required.").format(label))
	if len(text) > max_len:
		frappe.throw(_("{0} can be at most {1} characters.").format(label, max_len))
	return text


def clean_hhmm(value: str | None, label: str) -> str | None:
	"""Validate a 24-hour "HH:MM" wall-clock time (kept as text: Frappe fills empty Time fields with now)."""
	text = (value or "").strip()[:8]
	if not text:
		return None
	if len(text) == 8 and text.endswith(":00"):
		text = text[:5]  # accept HH:MM:00
	if not HH_MM.match(text):
		frappe.throw(_("{0} must be a time like 07:30.").format(label))
	return text
