import frappe
from frappe import _
from frappe.model.document import Document

from atomic_streak.constants import HABIT
from atomic_streak.doc_mixins import OwnedDocument
from atomic_streak.utils import clean_text, validate_color, validate_icon

MAX_STEPS = 20


class AtomicHabitRoutine(OwnedDocument, Document):
	def validate(self):
		self.validate_owner()
		self.routine_name = clean_text(self.routine_name, _("Routine name"), 140, required=True)
		self.cue = clean_text(self.cue, _("Cue"), 140)
		validate_color(self.color, _("Colour"))
		validate_icon(self.icon)
		if len(self.items) > MAX_STEPS:
			frappe.throw(_("A routine can have up to {0} habits.").format(MAX_STEPS))
		seen = set()
		for row in self.items:
			self.assert_same_user(HABIT, row.habit, _("Habit"))
			if row.habit in seen:
				frappe.throw(_("Each habit can appear only once in a routine."))
			seen.add(row.habit)
			row.cue_note = clean_text(row.cue_note, _("Note"), 140)

	def on_trash(self):
		self.on_trash_owner_check()
