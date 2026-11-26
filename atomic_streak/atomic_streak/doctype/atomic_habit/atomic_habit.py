from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from atomic_streak.constants import (
	CATEGORY,
	COMPLETION,
	MAX_DAILY_TARGET,
	MAX_INTERVAL_DAYS,
	PARTICIPATION,
	WEEKDAYS,
	Frequency,
	HabitStatus,
	HabitType,
)
from atomic_streak.doc_mixins import OwnedDocument
from atomic_streak.services import streaks
from atomic_streak.utils import clean_hhmm, clean_text, user_today, validate_color, validate_icon


class AtomicHabit(OwnedDocument, Document):
	def validate(self):
		self.validate_owner()
		self.habit_name = clean_text(self.habit_name, _("Habit name"), 140, required=True)
		self.description = clean_text(self.description, _("Description"), 1000)
		self.notes = clean_text(self.notes, _("Notes"), 4000)
		self.target_unit = clean_text(self.target_unit, _("Target unit"), 40) or "times"
		validate_color(self.color, _("Colour"))
		validate_icon(self.icon)
		self.validate_category()
		self.validate_schedule()
		self.validate_target()
		self.validate_reminder()
		self.track_pauses()

	def validate_category(self):
		if not self.category:
			return
		cat = frappe.db.get_value(CATEGORY, self.category, ["user", "is_standard"], as_dict=True)
		if not cat or not (cat.is_standard or cat.user == self.user):
			frappe.throw(_("Category not found."), frappe.DoesNotExistError)

	def validate_schedule(self):
		if not self.start_date:
			self.start_date = user_today(self.user)
		if self.end_date and getdate(self.end_date) < getdate(self.start_date):
			frappe.throw(_("End date can't be before the start date."))

		if self.frequency == Frequency.SPECIFIC_DAYS:
			days = {row.weekday for row in self.schedule if row.weekday in WEEKDAYS}
			if not days:
				frappe.throw(_("Pick at least one day of the week."))
			self.set("schedule", [{"weekday": d} for d in WEEKDAYS if d in days])
		else:
			self.set("schedule", [])

		if self.frequency == Frequency.EVERY_N_DAYS:
			if not (1 <= (self.interval_days or 0) <= MAX_INTERVAL_DAYS):
				frappe.throw(_("Repeat every 1 to {0} days.").format(MAX_INTERVAL_DAYS))
		else:
			self.interval_days = self.interval_days or 2

	def validate_target(self):
		if self.habit_type == HabitType.BREAK:
			# a "break" habit is tracked as one check-in per day: "I resisted today"
			self.daily_target, self.target_unit = 1, "day"
		if not (0 < (self.daily_target or 0) <= MAX_DAILY_TARGET):
			frappe.throw(_("Daily target must be more than 0."))

	def validate_reminder(self):
		self.preferred_time = clean_hhmm(self.preferred_time, _("Preferred time"))
		self.reminder_time = clean_hhmm(self.reminder_time, _("Reminder time"))
		if self.reminder_enabled and not self.reminder_time:
			frappe.throw(_("Choose a reminder time."))

	def track_pauses(self):
		"""Open a pause period when the habit stops being active; close it when it comes back."""
		previous = self.get_doc_before_save()
		old = previous.status if previous else None
		if old == self.status:
			return
		today = user_today(self.user)
		paused = (HabitStatus.PAUSED, HabitStatus.ARCHIVED)
		open_row = next((p for p in self.pauses if not p.to_date), None)
		if self.status in paused and not open_row:
			self.append("pauses", {"from_date": today})
		elif self.status == HabitStatus.ACTIVE and open_row:
			if getdate(open_row.from_date) >= today:
				self.remove(open_row)  # paused and resumed on the same day: no gap at all
			else:
				open_row.to_date = today - timedelta(days=1)

	def on_update(self):
		# schedule, dates or type may have changed: recompute from history
		streaks.refresh(self.name, self.user)

	def after_delete(self):
		# history and challenge entries went with the habit: refresh streaks, XP and rewards
		streaks.refresh(None, self.user)

	def on_trash(self):
		self.on_trash_owner_check()
		# A habit's history and memberships go with it (explicit user action).
		frappe.db.delete(COMPLETION, {"habit": self.name})
		frappe.db.delete(PARTICIPATION, {"habit": self.name})
		frappe.db.delete("Atomic Habit Routine Item", {"habit": self.name, "parenttype": "Atomic Habit Routine"})
