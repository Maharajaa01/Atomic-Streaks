"""The built-in coach: helpful without any AI provider.

Recognises a few intents (suggest habits, "I keep failing", weekly summary, motivation) and
answers from the user's own data. Replies are short, warm and never guilt-tripping.
"""

import random

from atomic_streak.services.coach.catalog import SUGGESTIONS, goals_in

ENCOURAGEMENT = [
	"Every check-in is a vote for the person you want to become.",
	"You don't need a perfect day. You need one small action.",
	"Missing once is an accident. Showing up again is the habit.",
	"Make it so easy you can't say no, then let it grow.",
	"Progress hides in the days that feel ordinary. Keep going.",
]


def _pick_suggestions(goals: list[str], limit: int = 3) -> list[dict]:
	out = []
	for g in goals or list(SUGGESTIONS):
		out += SUGGESTIONS.get(g, [])
	seen, unique = set(), []
	for s in out:
		if s["habit_name"] not in seen:
			seen.add(s["habit_name"])
			unique.append(s)
	return unique[:limit]


def weekly_summary(snap: dict) -> str:
	o = snap["overall"]
	if not snap["habits"]:
		return "You haven't added any habits yet. Start with one tiny habit and I'll have a summary for you next week."
	parts = []
	if o["rate_7d"] is not None:
		parts.append(f"This week you completed {o['rate_7d']}% of your scheduled habits.")
	if o["current_streak"]:
		parts.append(f"You're on a {o['current_streak']}-day streak.")
	if snap["best"]:
		parts.append(f"Going strong: {', '.join(snap['best'][:2])}.")
	if snap["struggling"]:
		parts.append(f"Worth making easier: {snap['struggling'][0]}. Try a two-minute version.")
	if o["bounce_backs_30d"]:
		parts.append(f"You bounced back after a missed day {o['bounce_backs_30d']} times this month. That's the real skill.")
	if snap["strongest_weekday"] and snap["weakest_weekday"] and snap["strongest_weekday"] != snap["weakest_weekday"]:
		parts.append(f"{snap['strongest_weekday']['weekday']} is your best day; {snap['weakest_weekday']['weekday']} could use a smaller plan.")
	return " ".join(parts) or "Keep checking in: your summary fills in as the week goes on."


def reply(message: str, snap: dict) -> dict:
	text = (message or "").lower()
	goals = goals_in(text)
	struggling = snap["struggling"]

	if any(w in text for w in ("fail", "keep missing", "can't stick", "cant stick", "struggl", "hard to", "give up", "quit")):
		target = next((h for h in snap["habits"] if h["name"].lower() in text), None)
		name = target["name"] if target else (struggling[0] if struggling else None)
		if name:
			return {
				"text": (
					f"Let's make {name} easier. Shrink it to a version you could do on your worst day, "
					f"like two minutes or two pages, and attach it to something you already do: "
					f"\"After I pour my morning tea, I will {name.lower()}\". Once it's automatic, grow it."
				),
				"suggestions": [],
			}
		return {"text": "Pick the habit that feels hardest and cut it down to two minutes. Easy beats ambitious when you're building a habit.", "suggestions": []}

	if any(w in text for w in ("summary", "this week", "how am i doing", "how did i do", "progress", "report")):
		return {"text": weekly_summary(snap), "suggestions": []}

	if goals or any(w in text for w in ("suggest", "idea", "new habit", "start", "recommend", "what should")):
		picks = _pick_suggestions(goals)
		lead = "Here are a few small habits to try" + (f" for {', '.join(goals)}" if goals else "") + ". Tap one to add it."
		return {"text": lead, "suggestions": picks}

	if any(w in text for w in ("motivat", "lazy", "tired of", "unmotivated", "encourage", "inspire")):
		return {"text": random.choice(ENCOURAGEMENT), "suggestions": []}

	return {
		"text": (
			"I can suggest habits for a goal (try \"habits for better sleep\"), help when a habit "
			"keeps slipping (\"I keep failing to read\"), or give you a weekly summary."
		),
		"suggestions": [],
	}
