"""The signed-in user's own profile and preferences."""

import frappe
from frappe import _

from atomic_streak.api.habit import _data, _user
from atomic_streak.constants import PROFILE
from atomic_streak.services.accounts import ensure_profile
from atomic_streak.rate_limits import per_user

EDITABLE = (
	"full_name",
	"timezone",
	"week_starts_on",
	"theme",
	"goals",
	"daily_reminder_enabled",
	"daily_reminder_time",
	"weekly_summary_enabled",
	"milestone_notifications",
)


@frappe.whitelist(methods=["POST"])
@per_user(120)
def update_profile(data) -> dict:
	user = _user()
	values = _data(data)
	profile = ensure_profile(user)
	for field in EDITABLE:
		if field in values:
			profile.set(field, values[field])
	if profile.daily_reminder_time and not frappe.utils.get_time_str(profile.daily_reminder_time):
		frappe.throw(_("Invalid reminder time."))
	profile.save(ignore_permissions=True)
	if "full_name" in values and profile.full_name:
		first, _sep, last = profile.full_name.partition(" ")
		frappe.db.set_value("User", user, {"first_name": first, "last_name": last.strip()})
	return {f: profile.get(f) for f in (*EDITABLE, "xp", "level") if f != "daily_reminder_time"} | {
		"daily_reminder_time": str(profile.daily_reminder_time or "")[:5]
	}
