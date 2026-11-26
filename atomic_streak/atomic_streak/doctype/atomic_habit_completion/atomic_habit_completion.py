import re
from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime

from atomic_streak.constants import COMPLETION, HABIT, MAX_DAILY_TARGET, CompletionStatus, HabitStatus, HabitType
from atomic_streak.doc_mixins import OwnedDocument
from atomic_streak.services import streaks, xp
from atomic_streak.utils import clean_text, is_admin, user_today

# How far back a user may record or change a completion. Keeps history honest: streaks can't
# be rebuilt months later, but a forgotten check-in from the last few days can be fixed.
BACKFILL_DAYS = 7
CLIENT_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


class AtomicHabitCompletion(OwnedDocument, Document):
	def validate(self):
		self.validate_owner()
		self.assert_same_user(HABIT, self.habit, _("Habit"))
		habit = frappe.db.get_value(
			HABIT, self.habit, ["status", "start_date", "end_date", "daily_target", "habit_type", "difficulty"], as_dict=True
		)
		self.validate_habit_state(habit)
		self.validate_date(habit)
		self.validate_value(habit)
		self.validate_client_id()
		self.note = clean_text(self.note, _("Note"), 500)
		self.validate_duplicate()
		self.xp_awarded = xp.checkin_xp(self.status, habit.difficulty, habit.habit_type)
		if self.is_new():
			self.completed_at = now_datetime()

	def validate_habit_state(self, habit):
		if self.is_new() and habit.status in (HabitStatus.ARCHIVED, HabitStatus.PAUSED):
			frappe.throw(_("This habit is {0}. Resume it to check in.").format(_(habit.status).lower()))

	def validate_date(self, habit):
		if not self.completion_date:
			self.completion_date = user_today(self.user)
		day = getdate(self.completion_date)
		today = user_today(self.user)
		if day > today:
			frappe.throw(_("You can't check in for a future date."))
		if day < getdate(habit.start_date):
			frappe.throw(_("This habit starts on {0}.").format(frappe.format(habit.start_date, "Date")))
		if habit.end_date and day > getdate(habit.end_date):
			frappe.throw(_("This habit ended on {0}.").format(frappe.format(habit.end_date, "Date")))
		if day < today - timedelta(days=BACKFILL_DAYS) and not is_admin():
			frappe.throw(_("Check-ins can only be changed for the last {0} days.").format(BACKFILL_DAYS))

	def validate_value(self, habit):
		if self.is_new() or not self.target:
			self.target = habit.daily_target or 1  # snapshot: later target changes don't rewrite history
		if habit.habit_type in (HabitType.BREAK, HabitType.ONE_TIME):
			self.value, self.target = 1, 1
		if self.value is None:
			self.value = self.target
		if not (0 < self.value <= MAX_DAILY_TARGET):
			frappe.throw(_("Enter an amount greater than 0."))
		self.status = CompletionStatus.COMPLETED if self.value >= self.target else CompletionStatus.PARTIAL

	def validate_client_id(self):
		if self.client_id and not CLIENT_ID.match(self.client_id):
			frappe.throw(_("Invalid client id."))
		if not self.is_new():
			previous = frappe.db.get_value(COMPLETION, self.name, "client_id")
			if previous and previous != self.client_id:
				self.client_id = previous

	def validate_duplicate(self):
		# Friendly message; the unique index below is what actually guarantees it.
		existing = frappe.db.get_value(
			COMPLETION, {"habit": self.habit, "completion_date": self.completion_date, "name": ["!=", self.name]}
		)
		if existing:
			frappe.throw(_("This habit is already checked in for that day."), frappe.DuplicateEntryError)

	def on_update(self):
		# covers insert and edits; numbers are recomputed from history in this transaction
		streaks.refresh(self.habit, self.user)

	def on_trash(self):
		self.on_trash_owner_check()

	def after_delete(self):
		streaks.refresh(self.habit, self.user)


def on_doctype_update():
	frappe.db.add_unique(COMPLETION, ["habit", "completion_date"], constraint_name="unique_habit_date")
	frappe.db.add_index(COMPLETION, ["user", "completion_date"], index_name="user_date")
