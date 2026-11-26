"""Push subscription and notification preferences (signed-in app user, own devices only)."""

import frappe
from frappe import _

from atomic_streak.api.habit import _user
from atomic_streak.constants import PROFILE
from atomic_streak.services import push
from atomic_streak.rate_limits import per_user


def _prefs(user: str) -> dict:
	p = frappe.db.get_value(
		PROFILE, user, ["daily_reminder_enabled", "daily_reminder_time", "weekly_summary_enabled", "milestone_notifications"], as_dict=True
	) or {}
	return {
		"daily_reminder_enabled": int(p.get("daily_reminder_enabled") or 0),
		"daily_reminder_time": str(p.get("daily_reminder_time") or "")[:5] or "08:00",
		"weekly_summary_enabled": int(p.get("weekly_summary_enabled") or 0),
		"milestone_notifications": int(p.get("milestone_notifications") or 0),
	}


@frappe.whitelist(methods=["GET"])
def get_push_config() -> dict:
	user = _user()
	return {**push.config(), "has_subscription": push.has_active(user), "prefs": _prefs(user)}


@frappe.whitelist(methods=["POST"])
@per_user(30)
def subscribe(subscription, user_agent: str | None = None) -> dict:
	user = _user()
	if not push.config()["enabled"]:
		frappe.throw(_("Notifications are switched off for this site."))
	return push.subscribe(user, frappe.parse_json(subscription) if isinstance(subscription, str) else subscription, user_agent)


@frappe.whitelist(methods=["POST"])
@per_user(30)
def unsubscribe(endpoint: str) -> dict:
	push.unsubscribe(_user(), endpoint)
	return {"ok": True}


@frappe.whitelist(methods=["POST"])
@per_user(5)
def send_test() -> dict:
	user = _user()
	sent = push.send(user, "Notifications are on", "This is how Atomic Streak reminders will look.", tag="test", kind="test", ttl=600)
	if not sent:
		frappe.throw(_("Couldn't reach this device. Try switching notifications off and on again."))
	return {"sent": sent}
