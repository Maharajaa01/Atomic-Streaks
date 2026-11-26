"""Ownership rules shared by every user-owned Atomic Streak DocType.

End users have no DocType permissions at all; they reach their data only through
atomic_streak.api.*, which filters by the session user. These controller checks are the second
line of defence: whatever path a document is saved through (API, Desk, import, background job),
a non-admin can never write a record that belongs to someone else, and a record can never be
moved to another user.
"""

import frappe
from frappe import _

from atomic_streak.utils import is_admin


class OwnedDocument:
	def validate_owner(self):
		session_user = frappe.session.user
		if not self.user:
			if session_user in (None, "Guest"):
				frappe.throw(_("A user is required."), frappe.PermissionError)
			self.user = session_user

		if not self.is_new():
			previous = frappe.db.get_value(self.doctype, self.name, "user")
			if previous and previous != self.user:
				frappe.throw(_("Records cannot be moved to another user."), frappe.PermissionError)

		if self.flags.ignore_owner_check:
			return  # set only by trusted server code (e.g. creating a profile during sign-up)

		if self.user != session_user and not is_admin(session_user):
			frappe.throw(_("You can only change your own records."), frappe.PermissionError)

	def on_trash_owner_check(self):
		if self.user != frappe.session.user and not is_admin():
			frappe.throw(_("You can only delete your own records."), frappe.PermissionError)

	def assert_same_user(self, doctype: str, name: str | None, label: str):
		"""A linked record (habit, routine...) must belong to the same user as this one."""
		if not name:
			return
		owner = frappe.db.get_value(doctype, name, "user")
		if owner != self.user:
			# same message whether it doesn't exist or belongs to someone else: no probing
			frappe.throw(_("{0} not found.").format(label), frappe.DoesNotExistError)
