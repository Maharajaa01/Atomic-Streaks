"""Web Push (VAPID), self-hosted: no third-party notification service, no API keys in the browser.

* The site's VAPID key pair is created once (on install/migrate) and kept in Atomic Streak
  Settings; the private key is a Password field and never leaves the server.
* Browsers hand us a subscription (endpoint + keys). We only ever POST to endpoints that belong
  to a real browser push service (see PUSH_HOSTS), so a client can't make the server send
  requests to arbitrary URLs (SSRF).
* Gone subscriptions (404/410) are switched off at once; others after repeated failures.
"""

import base64
import json
from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.utils import cint, get_url, now_datetime

from atomic_streak.constants import PROFILE, SETTINGS, SUBSCRIPTION

MAX_SUBSCRIPTIONS = 10
MAX_FAILURES = 5
TIMEOUT = 10

# Chrome/Edge/Opera (FCM: fcm.googleapis.com and Google hosts such as jmt17.google.com),
# Firefox (Mozilla autopush), Safari (Apple), legacy Edge (WNS). Only these companies' hosts.
PUSH_HOSTS = (
	"fcm.googleapis.com",
	"android.googleapis.com",
	".google.com",
	".push.services.mozilla.com",
	"updates.push.services.mozilla.com",
	"web.push.apple.com",
	".push.apple.com",
	".notify.windows.com",
)


def b64url(data: bytes) -> str:
	return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def is_push_endpoint(endpoint: str) -> bool:
	try:
		url = urlparse(endpoint)
	except ValueError:
		return False
	host = (url.hostname or "").lower()
	if url.scheme != "https" or not host or url.port not in (None, 443):
		return False
	return any(host == h.lstrip(".") or (h.startswith(".") and host.endswith(h)) for h in PUSH_HOSTS)


def site_url() -> str:
	"""Public https address of the site (push services reject http and odd ports in `sub`)."""
	host = frappe.conf.get("host_name") or get_url()
	url = urlparse(host if "://" in host else f"https://{host}")
	return f"https://{url.hostname}" if url.hostname else "https://localhost"


# ------------------------------------------------------------------ keys
def ensure_vapid_keys() -> None:
	"""Create the site's VAPID key pair if there isn't one. Never replaces an existing pair:
	that would silently break every subscription already made with the old public key."""
	settings = frappe.get_single(SETTINGS)
	if settings.vapid_public_key and settings.get_password("vapid_private_key", raise_exception=False):
		return
	from cryptography.hazmat.primitives import serialization
	from cryptography.hazmat.primitives.asymmetric import ec

	key = ec.generate_private_key(ec.SECP256R1())
	private = key.private_numbers().private_value.to_bytes(32, "big")
	public = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
	settings.vapid_public_key = b64url(public)
	settings.vapid_private_key = b64url(private)
	if not settings.vapid_subject:
		settings.vapid_subject = site_url()
	settings.flags.ignore_permissions = True
	settings.save()


def config() -> dict:
	settings = frappe.get_cached_doc(SETTINGS)
	enabled = bool(settings.push_enabled and settings.vapid_public_key)
	return {"enabled": enabled, "public_key": settings.vapid_public_key if enabled else None}


def _vapid():
	from py_vapid import Vapid02

	settings = frappe.get_cached_doc(SETTINGS)
	private = settings.get_password("vapid_private_key", raise_exception=False)
	if not (settings.push_enabled and private):
		return None, None
	subject = (settings.vapid_subject or site_url()).strip()
	if not subject.startswith(("mailto:", "https://")):
		subject = site_url()
	return Vapid02.from_raw(private.encode()), {"sub": subject}


# ------------------------------------------------------------------ subscriptions
def subscribe(user: str, subscription: dict, user_agent: str | None = None) -> dict:
	from atomic_streak.atomic_streak.doctype.atomic_notification_subscription.atomic_notification_subscription import (
		endpoint_hash,
	)

	if not isinstance(subscription, dict):
		frappe.throw(_("Invalid push subscription."))
	endpoint = str(subscription.get("endpoint") or "").strip()
	keys = subscription.get("keys") or {}
	if not is_push_endpoint(endpoint) or not isinstance(keys, dict):
		frappe.throw(_("This browser's push service isn't supported."))

	name = frappe.db.get_value(SUBSCRIPTION, {"endpoint_hash": endpoint_hash(endpoint)})
	if name and frappe.db.get_value(SUBSCRIPTION, name, "user") != user:
		# same browser, now signed in as someone else: the old owner must stop getting its pushes.
		# Server-side cleanup (plain row, no children), so it bypasses the per-user delete check.
		frappe.db.delete(SUBSCRIPTION, name)
		name = None
	if not name and frappe.db.count(SUBSCRIPTION, {"user": user}) >= MAX_SUBSCRIPTIONS:
		oldest = frappe.get_all(SUBSCRIPTION, filters={"user": user}, order_by="modified asc", limit=1, pluck="name")
		frappe.db.delete(SUBSCRIPTION, oldest[0])

	doc = frappe.get_doc(SUBSCRIPTION, name) if name else frappe.new_doc(SUBSCRIPTION)
	doc.update(
		{
			"user": user,
			"endpoint": endpoint,
			"p256dh": str(keys.get("p256dh") or ""),
			"auth": str(keys.get("auth") or ""),
			"user_agent": (user_agent or "")[:255],
			"is_active": 1,
			"failure_count": 0,
		}
	)
	doc.flags.ignore_owner_check = True
	doc.save(ignore_permissions=True) if name else doc.insert(ignore_permissions=True)
	return {"ok": True}


def unsubscribe(user: str, endpoint: str) -> None:
	from atomic_streak.atomic_streak.doctype.atomic_notification_subscription.atomic_notification_subscription import (
		endpoint_hash,
	)

	for name in frappe.get_all(SUBSCRIPTION, filters={"user": user, "endpoint_hash": endpoint_hash(endpoint or "")}, pluck="name"):
		frappe.db.delete(SUBSCRIPTION, name)


def has_active(user: str) -> bool:
	return bool(frappe.db.exists(SUBSCRIPTION, {"user": user, "is_active": 1}))


# ------------------------------------------------------------------ sending
def send(user: str, title: str, body: str, url: str = "/atomic-streak", tag: str | None = None, kind: str = "reminder", ttl: int = 4 * 3600) -> int:
	"""Push one notification to every active device of `user`. Returns how many accepted it."""
	from pywebpush import WebPushException, webpush

	vapid, claims = _vapid()
	if not vapid:
		return 0
	payload = json.dumps({"title": title, "body": body, "url": url, "tag": tag or kind, "kind": kind})
	sent = 0
	for sub in frappe.get_all(SUBSCRIPTION, filters={"user": user, "is_active": 1}, fields=["name", "endpoint", "p256dh", "auth", "failure_count"]):
		if not is_push_endpoint(sub.endpoint):
			frappe.db.set_value(SUBSCRIPTION, sub.name, "is_active", 0, update_modified=False)
			continue
		try:
			webpush(
				{"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}},
				data=payload,
				vapid_private_key=vapid,
				vapid_claims=dict(claims),
				ttl=ttl,
				timeout=TIMEOUT,
				headers={"Urgency": "normal"},
			)
			frappe.db.set_value(SUBSCRIPTION, sub.name, {"last_success": now_datetime(), "failure_count": 0}, update_modified=False)
			sent += 1
		except WebPushException as e:
			status = getattr(e.response, "status_code", None)
			gone = status in (404, 410)
			failures = cint(sub.failure_count) + 1
			frappe.db.set_value(
				SUBSCRIPTION,
				sub.name,
				{"failure_count": failures, "is_active": 0 if gone or failures >= MAX_FAILURES else 1},
				update_modified=False,
			)
			if not gone:
				frappe.log_error(title=f"Atomic Streak push failed ({status})", message=str(e)[:1000])
		except Exception:
			# network trouble: count it, keep the subscription, try again next time. Written to the
			# app log file too, since a failing request rolls back the database row.
			frappe.logger("atomic_streak").warning("push send failed", exc_info=True)
			frappe.db.set_value(SUBSCRIPTION, sub.name, "failure_count", cint(sub.failure_count) + 1, update_modified=False)
	return sent


def send_milestone(user: str, title: str, body: str) -> None:
	"""Badge earned / challenge finished. Runs as a background job after the check-in commits."""
	if not frappe.db.get_value(PROFILE, user, "milestone_notifications"):
		return
	send(user, title, body, url="/atomic-streak/challenges?tab=badges", tag=f"milestone-{frappe.generate_hash(length=6)}", kind="milestone", ttl=24 * 3600)
