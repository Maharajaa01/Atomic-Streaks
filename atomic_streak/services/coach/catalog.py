"""Starter habits the coach can suggest, grouped by the goals people usually mention.

Each suggestion is deliberately tiny (the "two-minute rule"): easy to start, easy to grow.
"""

SUGGESTIONS: dict[str, list[dict]] = {
	"sleep": [
		{"habit_name": "Phone away at 10 PM", "icon": "phone-off", "color": "#5B6B8C", "category": "Health", "time_of_day": "Night", "why": "Screens late at night push sleep back."},
		{"habit_name": "Lights out by 11", "icon": "moon", "color": "#7657F6", "category": "Health", "time_of_day": "Night", "why": "A steady bedtime is the strongest sleep habit."},
	],
	"fitness": [
		{"habit_name": "Walk 10 minutes", "icon": "footprints", "color": "#26C281", "category": "Fitness", "daily_target": 10, "target_unit": "minutes", "why": "Short walks are easy to start and add up."},
		{"habit_name": "5 push-ups", "icon": "dumbbell", "color": "#FF9F43", "category": "Fitness", "daily_target": 5, "target_unit": "push-ups", "time_of_day": "Morning", "why": "Small enough to never skip; grow it later."},
	],
	"reading": [
		{"habit_name": "Read 2 pages", "icon": "book-open", "color": "#7657F6", "category": "Reading", "daily_target": 2, "target_unit": "pages", "time_of_day": "Evening", "why": "Two pages turns into twenty on good days."},
	],
	"learning": [
		{"habit_name": "Practise 5 minutes", "icon": "graduation-cap", "color": "#4D8DFF", "category": "Learning", "daily_target": 5, "target_unit": "minutes", "why": "Little and often beats a long weekly session."},
	],
	"stress": [
		{"habit_name": "Breathe for 2 minutes", "icon": "flower-2", "color": "#9B7BFF", "category": "Mindfulness", "daily_target": 2, "target_unit": "minutes", "time_of_day": "Morning", "why": "A calm start sets the tone for the day."},
		{"habit_name": "Write one line in a journal", "icon": "notebook-pen", "color": "#1FB5A8", "category": "Personal Development", "time_of_day": "Evening", "why": "Naming the day helps you let it go."},
	],
	"health": [
		{"habit_name": "Drink a glass of water after waking", "icon": "glass-water", "color": "#4D8DFF", "category": "Health", "time_of_day": "Morning", "why": "Easy win, anchored to something you already do."},
		{"habit_name": "No sugary drinks", "icon": "candy-off", "color": "#F56FA1", "category": "Health", "habit_type": "Break", "why": "One clear rule is easier than counting."},
	],
	"money": [
		{"habit_name": "Log today's spending", "icon": "wallet", "color": "#26C281", "category": "Finance", "time_of_day": "Evening", "why": "Noticing spending changes it."},
		{"habit_name": "Save a small amount", "icon": "piggy-bank", "color": "#FFB020", "category": "Finance", "why": "The habit matters more than the amount."},
	],
	"focus": [
		{"habit_name": "Plan tomorrow's top task", "icon": "target", "color": "#FF9F43", "category": "Productivity", "time_of_day": "Evening", "why": "Deciding the night before saves willpower."},
		{"habit_name": "25 minutes of focused work", "icon": "timer", "color": "#7657F6", "category": "Work", "daily_target": 25, "target_unit": "minutes", "why": "One protected block beats a scattered day."},
	],
}

KEYWORDS = {
	"sleep": ("sleep", "tired", "bed", "insomnia", "rest"),
	"fitness": ("fit", "exercise", "workout", "gym", "run", "walk", "weight", "strong", "active"),
	"reading": ("read", "book"),
	"learning": ("learn", "study", "language", "skill", "course", "practice", "practise"),
	"stress": ("stress", "anxious", "anxiety", "calm", "mindful", "meditat", "overwhelm"),
	"health": ("health", "water", "eat", "diet", "sugar", "energy"),
	"money": ("money", "save", "saving", "spend", "budget", "finance", "debt"),
	"focus": ("focus", "productiv", "procrastinat", "work", "distract"),
}


def goals_in(text: str) -> list[str]:
	low = (text or "").lower()
	return [goal for goal, words in KEYWORDS.items() if any(w in low for w in words)]
