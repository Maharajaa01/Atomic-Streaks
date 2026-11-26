import re

import frappe
from frappe import _
from frappe.model.document import Document

from atomic_streak.utils import validate_color, validate_icon

CODE = re.compile(r"^[a-z0-9_]{2,64}$")


class AtomicAchievement(Document):
	def validate(self):
		if not CODE.match(self.code or ""):
			frappe.throw(_("Code may contain only lowercase letters, numbers and underscores."))
		if (self.threshold or 0) < 0 or (self.xp_reward or 0) < 0:
			frappe.throw(_("Threshold and XP reward can't be negative."))
		validate_color(self.color, _("Colour"))
		validate_icon(self.icon)
