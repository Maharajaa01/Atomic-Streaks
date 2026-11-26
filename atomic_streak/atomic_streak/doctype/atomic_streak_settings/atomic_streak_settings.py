import frappe
from frappe import _
from frappe.model.document import Document

from atomic_streak.utils import clean_text


class AtomicStreakSettings(Document):
	def validate(self):
		self.ai_model = clean_text(self.ai_model, _("Model"), 100)
		if self.ai_enabled and not self.ai_model:
			frappe.throw(_("Enter a model name."))
		if self.ai_enabled and not self.get_password("ai_api_key", raise_exception=False):
			frappe.throw(_("Enter the API key to turn on the AI coach."))
		subject = clean_text(self.vapid_subject, _("VAPID contact"), 255)
		if subject and not subject.startswith(("mailto:", "https://")):
			frappe.throw(_("VAPID contact must start with mailto: or https://"))
		self.vapid_subject = subject
