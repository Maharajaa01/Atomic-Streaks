"""Sign-up, joining and password-reset endpoints for the /atomic-streak app.

Sign-in and sign-out use Frappe's standard /api/method/login and /api/method/logout, and the
reset page redeems its key with Frappe's standard update_password, so sessions, password
hashing, lockouts and 2FA all stay Frappe's.
"""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from atomic_streak.services import accounts
from atomic_streak.utils import require_login
from atomic_streak.rate_limits import per_user


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_auth_options() -> dict:
	"""What the sign-in screens may offer. Reveals nothing about any account."""
	return {"allow_signup": accounts.signup_enabled(), "can_reset_password": accounts.can_send_email()}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=60 * 60)  # per IP: a class can sign up together on one network
def register(full_name: str, email: str, password: str, timezone: str | None = None) -> dict:
	if frappe.session.user != "Guest":
		frappe.throw(_("You're already signed in."))
	user = accounts.create_account(full_name, email, password, timezone)
	frappe.local.login_manager.login_as(user)
	return {"ok": True}


@frappe.whitelist(methods=["POST"])
@per_user(10)
def join(timezone: str | None = None) -> dict:
	accounts.join(require_login(), timezone)
	return {"ok": True}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=60 * 60)  # per IP
@rate_limit(key="email", ip_based=False, limit=3, seconds=60 * 60)  # per address: no inbox flooding
def request_password_reset(email: str) -> dict:
	try:
		accounts.send_password_reset(email)
	except Exception:
		# never let an internal error reveal whether the account exists
		frappe.clear_messages()
		frappe.log_error(title="Atomic Streak: password reset failed")
	return {"ok": True}
