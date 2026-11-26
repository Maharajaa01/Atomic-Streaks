import hashlib

import frappe
from frappe import _
from frappe.model.document import Document

from atomic_streak.doc_mixins import OwnedDocument
from atomic_streak.utils import clean_text


def endpoint_hash(endpoint: str) -> str:
	return hashlib.sha256(endpoint.encode()).hexdigest()


class AtomicNotificationSubscription(OwnedDocument, Document):
	def validate(self):
		self.validate_owner()
		self.endpoint = (self.endpoint or "").strip()
		if not self.endpoint.startswith("https://") or len(self.endpoint) > 2048:
			frappe.throw(_("Invalid push subscription."))
		self.endpoint_hash = endpoint_hash(self.endpoint)
		self.p256dh = clean_text(self.p256dh, "p256dh", 255, required=True)
		self.auth = clean_text(self.auth, "auth", 255, required=True)
		self.user_agent = clean_text(self.user_agent, "user agent", 255)[:255]

	def on_trash(self):
		self.on_trash_owner_check()
