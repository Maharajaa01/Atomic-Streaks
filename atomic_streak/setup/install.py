"""Install / migrate setup: roles, default settings and the built-in catalogue.

Safe to run repeatedly. Built-in records are created when missing and never overwritten, so
edits an administrator makes in Desk survive every migrate.
"""

import frappe

from atomic_streak.constants import ACHIEVEMENT, CATEGORY, CHALLENGE, ROLE_MANAGER, ROLE_USER, SETTINGS

ROLES = {
	ROLE_USER: {"desk_access": 0},
	ROLE_MANAGER: {"desk_access": 1},
}

# (name, lucide icon, colour)
CATEGORIES = [
	("Health", "heart-pulse", "#F56FA1"),
	("Fitness", "dumbbell", "#FF9F43"),
	("Learning", "graduation-cap", "#4D8DFF"),
	("Reading", "book-open", "#7657F6"),
	("Finance", "wallet", "#26C281"),
	("Productivity", "zap", "#FFB020"),
	("Mindfulness", "flower-2", "#9B7BFF"),
	("Personal Development", "sprout", "#1FB5A8"),
	("Relationships", "users", "#FF6B8B"),
	("Work", "briefcase", "#5B6B8C"),
	("Custom", "sparkles", "#A0AEC0"),
]

# (code, title, description, criteria, threshold, xp, icon, colour)
ACHIEVEMENTS = [
	("first_completion", "First Step", "Completed your very first habit.", "First Completion", 1, 20, "footprints", "#26C281"),
	("streak_3", "Warming Up", "Reached a 3-day streak.", "Streak", 3, 30, "flame", "#FF9F43"),
	("streak_7", "One Week Strong", "Reached a 7-day streak.", "Streak", 7, 70, "flame", "#F56FA1"),
	("streak_30", "Habit Master", "Reached a 30-day streak.", "Streak", 30, 300, "crown", "#7657F6"),
	("completions_100", "Century", "Completed 100 habits in total.", "Total Completions", 100, 200, "medal", "#4D8DFF"),
	("weekly_90", "Consistency Champion", "Hit 90% of your scheduled habits in a week.", "Weekly Consistency", 90, 100, "target", "#FFD166"),
	("first_challenge", "Challenger", "Finished your first challenge.", "Challenge Completed", 1, 50, "trophy", "#FF9F43"),
	("habits_5", "Habit Builder", "Created 5 habits.", "Habits Created", 5, 25, "layers", "#1FB5A8"),
]

# (code, title, type, description, suggested habit, xp, icon, colour)
CHALLENGES = [
	("drink_water_7", "7 Days of Hydration", "7-Day", "Drink 8 glasses of water every day for a week.", "Drink 8 glasses of water", 70, "glass-water", "#4D8DFF"),
	("read_21", "21-Day Reading Habit", "21-Day", "Read at least 10 pages every day for 21 days.", "Read 10 pages", 210, "book-open", "#7657F6"),
	("mindful_21", "21 Mindful Mornings", "21-Day", "Meditate for 5 minutes each morning.", "Meditate 5 minutes", 210, "flower-2", "#9B7BFF"),
	("move_30", "30 Days of Movement", "30-Day", "Move your body for 15 minutes every day.", "Exercise 15 minutes", 300, "dumbbell", "#FF9F43"),
	("no_sugar_7", "7 Days Sugar-Free", "7-Day", "Skip added sugar for a full week.", "No added sugar", 70, "candy-off", "#F56FA1"),
]


def after_install():
	setup()


def after_migrate():
	setup()


def setup():
	frappe.flags.in_install = True
	try:
		create_roles()
		set_default_settings()
		create_categories()
		create_achievements()
		create_challenges()
		from atomic_streak.services.push import ensure_vapid_keys

		ensure_vapid_keys()  # needed before anyone can subscribe; never replaces an existing pair
	finally:
		frappe.flags.in_install = False


def create_roles():
	for role_name, props in ROLES.items():
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc({"doctype": "Role", "role_name": role_name, **props}).insert(ignore_permissions=True)


def set_default_settings():
	# get_single() fills field defaults in memory, so check what is actually stored
	if frappe.db.exists("Singles", {"doctype": SETTINGS}):
		return
	settings = frappe.get_single(SETTINGS)
	settings.ai_model = settings.ai_model or "claude-opus-5-5"
	settings.weekly_summary_day = settings.weekly_summary_day or "Sunday"
	settings.allow_signup = 1
	settings.flags.ignore_permissions = True
	settings.save()


def create_categories():
	for i, (name, icon, color) in enumerate(CATEGORIES):
		if frappe.db.exists(CATEGORY, name):
			continue
		doc = frappe.get_doc(
			{"doctype": CATEGORY, "category_name": name, "is_standard": 1, "icon": icon, "color": color, "sort_order": i}
		)
		doc.flags.in_install = True
		doc.insert(ignore_permissions=True)


def create_achievements():
	for i, (code, title, desc, criteria, threshold, xp, icon, color) in enumerate(ACHIEVEMENTS):
		if frappe.db.exists(ACHIEVEMENT, code):
			continue
		frappe.get_doc(
			{
				"doctype": ACHIEVEMENT,
				"code": code,
				"title": title,
				"description": desc,
				"criteria": criteria,
				"threshold": threshold,
				"xp_reward": xp,
				"icon": icon,
				"color": color,
				"sort_order": i,
			}
		).insert(ignore_permissions=True)


def create_challenges():
	for i, (code, title, ctype, desc, habit, xp, icon, color) in enumerate(CHALLENGES):
		if frappe.db.exists(CHALLENGE, {"code": code}):
			continue
		frappe.get_doc(
			{
				"doctype": CHALLENGE,
				"code": code,
				"title": title,
				"challenge_type": ctype,
				"duration_days": {"7-Day": 7, "21-Day": 21, "30-Day": 30}[ctype],
				"description": desc,
				"suggested_habit": habit,
				"xp_reward": xp,
				"icon": icon,
				"color": color,
				"is_standard": 1,
				"sort_order": i,
			}
		).insert(ignore_permissions=True)
