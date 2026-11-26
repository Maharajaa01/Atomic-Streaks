import frappe
from frappe import _
from frappe.model.document import Document

from atomic_streak.doc_mixins import OwnedDocument
from atomic_streak.utils import clean_hhmm, clean_text

PRIORITIES = ("Normal", "High", "Low")


class AtomicPlanTask(OwnedDocument, Document):
	def validate(self):
		self.validate_owner()
		self.title = clean_text(self.title, _("Task"), 140, required=True)
		self.notes = clean_text(self.notes, _("Notes"), 1000)
		self.start_time = clean_hhmm(self.start_time, _("Time"))
		if self.priority not in PRIORITIES:
			self.priority = "Normal"
		if self.is_done and not self.done_at:
			self.done_at = frappe.utils.now_datetime()
		elif not self.is_done:
			self.done_at = None

	def on_trash(self):
		self.on_trash_owner_check()
