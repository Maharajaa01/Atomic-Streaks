from frappe import _
from frappe.model.document import Document

from atomic_streak.doc_mixins import OwnedDocument
from atomic_streak.utils import clean_text

MAX_MESSAGE = 8000


class AtomicCoachConversation(OwnedDocument, Document):
	def validate(self):
		self.validate_owner()
		self.title = clean_text(self.title, _("Title"), 140) or _("Coaching chat")
		for row in self.messages:
			row.content = clean_text(row.content, _("Message"), MAX_MESSAGE, required=True)

	def on_trash(self):
		self.on_trash_owner_check()
