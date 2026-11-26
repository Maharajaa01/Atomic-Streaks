"""Per-person rate limits for signed-in endpoints.

Frappe's @rate_limit counts per IP address. Many Atomic Streak users share one public IP (a
school or office network), so an IP budget would let one person use up everyone's allowance.
Signed-in actions are therefore limited per user; guest endpoints (sign-up, password reset)
keep Frappe's IP-based limit.

Like Frappe's limiter, this only applies to real HTTP requests (not tests or background jobs).
"""

from functools import wraps

import frappe
from frappe import _


def per_user(limit: int, seconds: int = 3600):
	def decorator(fn):
		@wraps(fn)
		def wrapper(*args, **kwargs):
			user = frappe.session.user if getattr(frappe.local, "session", None) else None
			if not frappe.request or not user or user == "Guest":
				return fn(*args, **kwargs)
			key = frappe.cache.make_key(f"rl:atomic:{fn.__module__}.{fn.__name__}:{user}")
			count = frappe.cache.incrby(key, 1)
			if count == 1:
				frappe.cache.expire(key, seconds)
			if count > limit:
				frappe.throw(_("You've done that a lot just now. Please wait a little and try again."), frappe.RateLimitExceededError)
			return fn(*args, **kwargs)

		return wrapper

	return decorator
