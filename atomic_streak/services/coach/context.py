"""A compact, private snapshot of one user's habits for the coach (rules or AI).

Only that user's own data is read. It is what the AI provider sees when AI is enabled.
"""

import frappe

from atomic_streak.constants import PROFILE
from atomic_streak.services import analytics


def snapshot(user: str) -> dict:
	data = analytics.dashboard(user, 30)
	profile = frappe.db.get_value(PROFILE, user, ["full_name", "goals", "current_streak", "longest_streak", "xp", "level"], as_dict=True) or {}
	first = (profile.get("full_name") or "").split(" ")[0]
	habits = [
		{
			"name": h["habit_name"],
			"rate_30d": h["rate"],
			"missed_30d": h["missed"],
			"current_streak": h["current_streak"],
			"best_streak": h["longest_streak"],
			"status": h["status"],
		}
		for h in data["habits"]
	]
	return {
		"first_name": first,
		"goals": profile.get("goals") or "",
		"overall": {
			"rate_30d": data["rate"],
			"rate_7d": data["week_rate"],
			"previous_30d": data["previous_rate"],
			"current_streak": data["streak"]["current"],
			"best_streak": data["streak"]["longest"],
			"bounce_backs_30d": data["comebacks"],
		},
		"strongest_weekday": max((w for w in data["weekdays"] if w["rate"] is not None), key=lambda w: w["rate"], default=None),
		"weakest_weekday": min((w for w in data["weekdays"] if w["rate"] is not None), key=lambda w: w["rate"], default=None),
		"habits": habits,
		"struggling": [h["habit_name"] for h in data["struggling"][:3]],
		"best": [h["habit_name"] for h in data["best"][:3]],
	}


def as_text(snap: dict) -> str:
	"""Plain-text version for the AI provider (kept small and factual)."""
	o = snap["overall"]
	lines = [
		f"Name: {snap['first_name'] or 'unknown'}",
		f"Stated goals: {snap['goals'] or 'not given'}",
		f"Last 30 days: {o['rate_30d']}% of scheduled habits done (previous 30 days: {o['previous_30d']}%). Last 7 days: {o['rate_7d']}%.",
		f"Overall streak: {o['current_streak']} days (best {o['best_streak']}). Bounced back after a miss {o['bounce_backs_30d']} times.",
	]
	if snap["strongest_weekday"]:
		lines.append(f"Strongest weekday: {snap['strongest_weekday']['weekday']}; weakest: {snap['weakest_weekday']['weekday']}.")
	if snap["habits"]:
		lines.append("Habits (30-day completion, misses, current/best streak):")
		lines += [
			f"- {h['name']}: {h['rate_30d'] if h['rate_30d'] is not None else 'n/a'}%, missed {h['missed_30d']}, streak {h['current_streak']}/{h['best_streak']}{' (paused)' if h['status'] == 'Paused' else ''}"
			for h in snap["habits"]
		]
	else:
		lines.append("No habits yet.")
	return "\n".join(lines)
