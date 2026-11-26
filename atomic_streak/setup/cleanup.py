"""When a Frappe User is deleted, remove everything Atomic Streak stored for them.

Runs from the User on_trash hook, which Frappe calls before its linked-document check, so
deleting a user isn't blocked by their habits and their private data doesn't outlive them.
"""

import frappe

from atomic_streak.constants import CATEGORY, CHALLENGE, USER_OWNED


def on_user_trash(doc, method=None):
	user = doc.name
	child_tables = {
		"Atomic Habit": ("Atomic Habit Schedule", "Atomic Habit Pause"),
		"Atomic Habit Routine": ("Atomic Habit Routine Item",),
		"Atomic Coach Conversation": ("Atomic Coach Message",),
	}
	for doctype in USER_OWNED:
		names = frappe.get_all(doctype, filters={"user": user}, pluck="name")
		if not names:
			continue
		for child in child_tables.get(doctype, ()):
			frappe.db.delete(child, {"parenttype": doctype, "parent": ["in", names]})
		frappe.db.delete(doctype, {"name": ["in", names]})

	# the user's custom categories / challenges (built-in ones have no owner)
	custom_challenges = frappe.get_all(CHALLENGE, filters={"created_by_user": user, "is_standard": 0}, pluck="name")
	if custom_challenges:
		frappe.db.delete("Atomic Challenge Participation", {"challenge": ["in", custom_challenges]})
		frappe.db.delete(CHALLENGE, {"name": ["in", custom_challenges]})
	frappe.db.delete(CATEGORY, {"user": user, "is_standard": 0})
