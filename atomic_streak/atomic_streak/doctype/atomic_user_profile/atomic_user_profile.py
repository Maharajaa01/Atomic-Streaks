import frappe
from frappe import _
from frappe.model.document import Document

from atomic_streak.doc_mixins import OwnedDocument
from atomic_streak.utils import clean_text, is_valid_timezone


class AtomicUserProfile(OwnedDocument, Document):
	def before_insert(self):
		# named after the user (autoname field:user), and naming runs before validate
		if not self.user and frappe.session.user != "Guest":
			self.user = frappe.session.user

	def validate(self):
		self.validate_owner()
		self.full_name = clean_text(self.full_name, _("Name"), 140)
		self.goals = clean_text(self.goals, _("Goals"), 1000)
		if self.timezone and not is_valid_timezone(self.timezone):
			frappe.throw(_("Unknown timezone {0}.").format(frappe.bold(self.timezone)))

	def on_trash(self):
		self.on_trash_owner_check()
