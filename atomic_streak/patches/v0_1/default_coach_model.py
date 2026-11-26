"""Move the untouched AI coach default from claude-sonnet-5-5 to claude-opus-5-5.

Only changes the value if the coach was never switched on and the model is still the old
default, so an administrator's own choice is never overwritten.
"""

import frappe


def execute():
	settings = "Atomic Streak Settings"
	if frappe.db.get_single_value(settings, "ai_enabled"):
		return
	if frappe.db.get_single_value(settings, "ai_model") == "claude-sonnet-5-5":
		frappe.db.set_single_value(settings, "ai_model", "claude-opus-5-5")
