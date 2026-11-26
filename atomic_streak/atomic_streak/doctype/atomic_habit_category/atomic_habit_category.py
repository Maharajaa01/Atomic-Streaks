import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname

from atomic_streak.constants import CATEGORY, HABIT
from atomic_streak.utils import clean_text, is_admin, validate_color, validate_icon

MAX_CUSTOM_CATEGORIES = 50


class AtomicHabitCategory(Document):
	def autoname(self):
		# built-in categories keep readable names ("Health"); custom ones get an opaque id
		self.name = self.category_name.strip() if self.is_standard else make_autoname("CAT-.#######")

	def validate(self):
		self.category_name = clean_text(self.category_name, _("Category name"), 60, required=True)
		validate_color(self.color, _("Colour"))
		validate_icon(self.icon)
		admin = is_admin()
		if self.is_standard:
			if not admin and not self.flags.in_install:
				frappe.throw(_("Only administrators can change built-in categories."), frappe.PermissionError)
			self.user = None
		else:
			if not self.user:
				self.user = frappe.session.user
			if self.user != frappe.session.user and not admin:
				frappe.throw(_("You can only change your own categories."), frappe.PermissionError)
			if self.is_new() and frappe.db.count(CATEGORY, {"user": self.user}) >= MAX_CUSTOM_CATEGORIES:
				frappe.throw(_("You can have up to {0} custom categories.").format(MAX_CUSTOM_CATEGORIES))
		self.validate_unique_name()

	def validate_unique_name(self):
		clash = frappe.db.sql(
			f"""select name from `tab{CATEGORY}`
			where lower(category_name) = lower(%(n)s) and name != %(name)s
			and (is_standard = 1 or ifnull(user, '') = %(user)s)
			limit 1""",
			{"n": self.category_name, "name": self.name or "", "user": self.user or ""},
		)
		if clash:
			frappe.throw(_("A category called {0} already exists.").format(frappe.bold(self.category_name)))

	def on_trash(self):
		if self.is_standard and not is_admin():
			frappe.throw(_("Built-in categories can't be deleted."), frappe.PermissionError)
		if not self.is_standard and self.user != frappe.session.user and not is_admin():
			frappe.throw(_("You can only delete your own categories."), frappe.PermissionError)
		frappe.db.set_value(HABIT, {"category": self.name}, "category", None, update_modified=False)
