from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from atomic_streak.constants import CHALLENGE, HABIT, PARTICIPATION, ParticipationStatus
from atomic_streak.doc_mixins import OwnedDocument
from atomic_streak.utils import user_today


class AtomicChallengeParticipation(OwnedDocument, Document):
	def validate(self):
		self.validate_owner()
		challenge = frappe.db.get_value(
			CHALLENGE, self.challenge, ["is_active", "is_standard", "created_by_user", "duration_days"], as_dict=True
		)
		# visible = built-in, or the user's own custom challenge
		if not challenge or not (challenge.is_standard or challenge.created_by_user == self.user):
			frappe.throw(_("Challenge not found."), frappe.DoesNotExistError)
		if self.is_new() and not challenge.is_active:
			frappe.throw(_("This challenge is no longer open."))
		self.assert_same_user(HABIT, self.habit, _("Habit"))

		if not self.start_date:
			self.start_date = user_today(self.user)
		self.end_date = getdate(self.start_date) + timedelta(days=(challenge.duration_days or 1) - 1)

		if self.status == ParticipationStatus.ACTIVE:
			clash = frappe.db.exists(
				PARTICIPATION,
				{"user": self.user, "challenge": self.challenge, "status": "Active", "name": ["!=", self.name]},
			)
			if clash:
				frappe.throw(_("You're already taking part in this challenge."))

	def on_trash(self):
		self.on_trash_owner_check()
