"""Accounts for Atomic Streak: sign-up, joining with an existing account, profiles, password reset.

Passwords are always Frappe's own (``frappe.utils.password``): nothing here stores or compares
passwords itself. App users are Website Users with only the "Atomic Streak User" role, so they
never get Desk access.
"""

import frappe
from frappe import _
from frappe.core.doctype.user.user import test_password_strength
from frappe.utils import escape_html, get_url, validate_email_address

from atomic_streak.constants import APP_ROUTE, PROFILE, ROLE_USER, SETTINGS
from atomic_streak.utils import clean_text, is_valid_timezone

MAX_PASSWORD = 100
MIN_PASSWORD = 8


def signup_enabled() -> bool:
	return bool(frappe.db.get_single_value(SETTINGS, "allow_signup"))


def can_send_email() -> bool:
	return bool(
		frappe.db.exists("Email Account", {"enable_outgoing": 1, "default_outgoing": 1}) or frappe.conf.get("mail_server")
	)


def has_access(user: str) -> bool:
	return ROLE_USER in frappe.get_roles(user)


def check_password_strength(password: str, user_data: tuple | None = None) -> None:
	password = password or ""
	if len(password) > MAX_PASSWORD:
		frappe.throw(_("That password is too long."))
	if len(password) < MIN_PASSWORD:
		frappe.throw(_("Use at least {0} characters.").format(MIN_PASSWORD))
	result = test_password_strength(password, user_data=user_data) or {}
	feedback = result.get("feedback") or {}
	if feedback and not feedback.get("password_policy_validation_passed", False):
		tips = " ".join(filter(None, [feedback.get("warning"), *(feedback.get("suggestions") or [])]))
		frappe.throw(_("That password is too easy to guess.") + (f" {tips}" if tips else ""))


def split_name(full_name: str) -> tuple[str, str]:
	first, _sep, last = full_name.partition(" ")
	return first.strip(), last.strip()


def create_account(full_name: str, email: str, password: str, timezone: str | None = None) -> str:
	"""Create a Website User with the app role and a profile. Returns the user name (email)."""
	if not signup_enabled():
		frappe.throw(_("Sign-up is closed right now."), frappe.PermissionError)

	full_name = clean_text(full_name, _("Name"), 140, required=True)
	email = (email or "").strip().lower()
	if len(email) > 140 or not validate_email_address(email):
		frappe.throw(_("Enter a valid email address."))
	if frappe.db.exists("User", email) or frappe.db.exists("User", {"email": email}):
		frappe.throw(_("An account with this email already exists. Sign in instead."), frappe.DuplicateEntryError)

	first, last = split_name(full_name)
	check_password_strength(password, user_data=(first, "", last, email, None))

	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": first,
			"last_name": last,
			"user_type": "Website User",
			"send_welcome_email": 0,
			"new_password": password,
			"roles": [{"role": ROLE_USER}],
		}
	)
	user.flags.no_welcome_mail = True
	user.flags.ignore_permissions = True
	user.flags.ignore_password_policy = True  # checked above with our own clearer messages
	user.insert()

	ensure_profile(user.name, timezone=timezone, full_name=full_name)
	return user.name


def join(user: str, timezone: str | None = None) -> None:
	"""Let a signed-in person who already has an account (e.g. ERP staff) start using the app.

	Only adds the app role, which grants no DocType or Desk access by itself.
	"""
	if user in ("Guest", "Administrator"):
		raise frappe.PermissionError
	if not has_access(user):
		if not signup_enabled():
			frappe.throw(_("Atomic Streak isn't open to new members right now."), frappe.PermissionError)
		doc = frappe.get_doc("User", user)
		doc.flags.ignore_permissions = True
		doc.add_roles(ROLE_USER)
	ensure_profile(user, timezone=timezone)


DEFAULT_DAILY_REMINDER = "08:00:00"


def ensure_profile(user: str, timezone: str | None = None, full_name: str | None = None):
	if frappe.db.exists(PROFILE, user):
		return frappe.get_doc(PROFILE, user)
	profile = frappe.get_doc(
		{
			"doctype": PROFILE,
			"user": user,
			"full_name": full_name or frappe.utils.get_fullname(user),
			"timezone": timezone if is_valid_timezone(timezone) else None,
			# explicit: Frappe fills an empty Time field with "now" on insert, which would put
			# everyone's daily reminder at the minute they signed up
			"daily_reminder_time": DEFAULT_DAILY_REMINDER,
		}
	)
	# During sign-up the new user isn't the session user yet; ownership is set explicitly here.
	profile.flags.ignore_owner_check = True
	profile.insert(ignore_permissions=True)
	return profile


def send_password_reset(email: str) -> None:
	"""Email a reset link that opens Atomic Streak's own reset page.

	Silent for unknown, disabled or non-app accounts so the response never reveals whether an
	email is registered. The key is Frappe's standard reset key (hashed in the database, single
	use, expiry from System Settings) and is redeemed by Frappe's own ``update_password``.
	"""
	email = (email or "").strip().lower()
	if not email or len(email) > 140 or not validate_email_address(email):
		return
	name = frappe.db.get_value("User", {"name": email, "enabled": 1}) or frappe.db.get_value(
		"User", {"email": email, "enabled": 1}
	)
	if not name or name == "Administrator" or not has_access(name):
		return

	user = frappe.get_doc("User", name)
	frappe_link = user._reset_password(send_email=False)
	key = frappe_link.split("key=", 1)[1].split("&", 1)[0]
	link = get_url(f"{APP_ROUTE}/reset-password?key={key}", allow_header_override=False)
	try:
		queued = frappe.sendmail(
			recipients=[user.email],
			subject=_("Reset your Atomic Streak password"),
			message=reset_email_html(user.first_name or "", link),
			now=True,
			retry=3,
		)
	except frappe.OutgoingEmailError:
		frappe.clear_messages()
		frappe.log_error(title="Atomic Streak: password reset email could not be sent")
		return
	# like Frappe's own reset mail: don't keep a usable link in the Email Queue
	if queued and getattr(queued, "name", None):
		frappe.db.set_value(
			"Email Queue", queued.name, "message", "[password reset link redacted]", update_modified=False
		)


def reset_email_html(first_name: str, link: str) -> str:
	name = escape_html(first_name)
	return f"""
<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:480px;margin:0 auto;padding:24px;color:#111827">
  <div style="background:linear-gradient(135deg,#7657F6,#4D8DFF);border-radius:20px;padding:28px;color:#fff;text-align:center">
    <div style="font-size:22px;font-weight:800">Atomic Streak</div>
    <div style="opacity:.85;font-size:14px;margin-top:4px">Small Habits. Remarkable Change.</div>
  </div>
  <p style="font-size:16px;margin:24px 0 8px">Hi {name},</p>
  <p style="font-size:15px;line-height:1.6;color:#374151">We got a request to reset your password. Tap the button below to choose a new one.</p>
  <p style="text-align:center;margin:28px 0">
    <a href="{link}" style="background:#7657F6;color:#fff;text-decoration:none;font-weight:700;padding:14px 28px;border-radius:14px;display:inline-block">Choose a new password</a>
  </p>
  <p style="font-size:13px;color:#6B7280;line-height:1.6">If you didn't ask for this, you can ignore this email. Your password won't change.</p>
</div>"""
