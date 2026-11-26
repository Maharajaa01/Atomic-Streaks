import frappe
from frappe import _
from frappe.model.document import Document

from atomic_streak.constants import CATEGORY, PARTICIPATION
from atomic_streak.utils import clean_text, is_admin, validate_color, validate_icon

FIXED_DURATIONS = {"7-Day": 7, "21-Day": 21, "30-Day": 30}
MAX_CUSTOM_DAYS = 365


class AtomicChallenge(Document):
	def validate(self):
		self.title = clean_text(self.title, _("Title"), 140, required=True)
		self.description = clean_text(self.description, _("Description"), 1000)
		self.suggested_habit = clean_text(self.suggested_habit, _("Suggested habit"), 140)
		validate_color(self.color, _("Colour"))
		validate_icon(self.icon)
		self.validate_owner()
		if self.challenge_type in FIXED_DURATIONS:
			self.duration_days = FIXED_DURATIONS[self.challenge_type]
		elif not (1 <= (self.duration_days or 0) <= MAX_CUSTOM_DAYS):
			frappe.throw(_("A custom challenge lasts 1 to {0} days.").format(MAX_CUSTOM_DAYS))
		if self.category:
			cat = frappe.db.get_value(CATEGORY, self.category, ["is_standard", "user"], as_dict=True)
			if not cat or not (cat.is_standard or cat.user == self.created_by_user):
				frappe.throw(_("Category not found."), frappe.DoesNotExistError)

	def validate_owner(self):
		if is_admin() or frappe.flags.in_install:
			return
		# non-admins (app users through the API) may only manage their own custom challenges
		if self.is_standard:
			frappe.throw(_("Only administrators can change built-in challenges."), frappe.PermissionError)
		if not self.created_by_user:
			self.created_by_user = frappe.session.user
		if self.created_by_user != frappe.session.user:
			frappe.throw(_("You can only change your own challenges."), frappe.PermissionError)
		if not self.is_new():
			previous = frappe.db.get_value(self.doctype, self.name, "created_by_user")
			if previous != self.created_by_user:
				frappe.throw(_("You can only change your own challenges."), frappe.PermissionError)

	def on_trash(self):
		if not is_admin():
			if self.is_standard or self.created_by_user != frappe.session.user:
				frappe.throw(_("You can only delete your own challenges."), frappe.PermissionError)
		frappe.db.delete(PARTICIPATION, {"challenge": self.name})
