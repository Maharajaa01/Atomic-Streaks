"""Boot data for the /atomic-streak app: who is signed in and their profile."""

import frappe

from atomic_streak.constants import PROFILE, SETTINGS
from atomic_streak.services import accounts
from atomic_streak.utils import get_user_timezone, require_login

PROFILE_FIELDS = (
	"full_name",
	"avatar",
	"timezone",
	"week_starts_on",
	"theme",
	"goals",
	"onboarding_completed",
	"xp",
	"level",
	"current_streak",
	"longest_streak",
	"total_completions",
)


@frappe.whitelist(methods=["GET"])
def get_boot() -> dict:
	user = require_login()
	boot = {
		"user": user,
		"full_name": frappe.utils.get_fullname(user),
		"user_image": frappe.db.get_value("User", user, "user_image"),
		"has_access": accounts.has_access(user),
		"allow_join": accounts.signup_enabled(),
	}
	if not boot["has_access"]:
		return boot

	profile = frappe.db.get_value(PROFILE, user, PROFILE_FIELDS, as_dict=True)
	boot["profile"] = profile or {"full_name": boot["full_name"], "xp": 0, "level": 1, "theme": "System"}
	boot["profile"]["timezone"] = get_user_timezone(user)
	boot["profile"]["has_timezone"] = bool(profile and profile.timezone)
	settings = frappe.get_cached_doc(SETTINGS)
	boot["features"] = {"ai_coach": bool(settings.ai_enabled), "push": bool(settings.push_enabled)}
	return boot
