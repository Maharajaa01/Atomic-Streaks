import frappe
from frappe import _
from frappe.model.document import Document

from atomic_streak.constants import USER_ACHIEVEMENT
from atomic_streak.doc_mixins import OwnedDocument


class AtomicUserAchievement(OwnedDocument, Document):
	def validate(self):
		self.validate_owner()
		if frappe.db.exists(
			USER_ACHIEVEMENT, {"user": self.user, "achievement": self.achievement, "name": ["!=", self.name]}
		):
			frappe.throw(_("Achievement already earned."), frappe.DuplicateEntryError)
		if self.is_new():
			self.achieved_on = frappe.utils.now_datetime()

	def on_trash(self):
		self.on_trash_owner_check()


def on_doctype_update():
	frappe.db.add_unique(USER_ACHIEVEMENT, ["user", "achievement"], constraint_name="unique_user_achievement")
