"""One entry point to keep rewards in step with history: challenges -> achievements -> XP.

Called (inside the same transaction) after any check-in or habit change, right after the
streak engine, so every reward is derived from up-to-date streaks and totals.
"""

import frappe

from atomic_streak.constants import CHALLENGE, PARTICIPATION, ParticipationStatus
from atomic_streak.services import achievements, challenges, xp


def refresh(user: str, habit: str | None = None) -> None:
	finished = challenges.recompute_for(user, habit)
	earned = achievements.evaluate(user)
	xp.recompute(user)
	_push_milestones(user, earned, finished)


def _push_milestones(user: str, earned: list[str], finished: list[str]) -> None:
	"""Tell the user's other devices. Sent after commit, so an undone/failed request sends nothing."""
	if not (earned or finished):
		return
	from atomic_streak.constants import ACHIEVEMENT

	messages = []
	for code in earned:
		title, description = frappe.db.get_value(ACHIEVEMENT, code, ["title", "description"]) or (code, "")
		messages.append((f"New badge: {title}", description))
	for name in finished:
		title = frappe.db.get_value(CHALLENGE, frappe.db.get_value(PARTICIPATION, name, "challenge"), "title")
		messages.append(("Challenge complete!", f"You finished {title}."))
	for title, body in messages:
		frappe.enqueue(
			"atomic_streak.services.push.send_milestone",
			queue="short",
			enqueue_after_commit=True,
			user=user,
			title=title,
			body=body,
		)


def pending_celebrations(user: str) -> dict:
	done = frappe.get_all(
		PARTICIPATION,
		filters={"user": user, "status": ParticipationStatus.COMPLETED, "celebrated": 0},
		fields=["name", "challenge", "xp_awarded"],
	)
	info = {c.name: c for c in frappe.get_all(CHALLENGE, filters={"name": ["in", [d.challenge for d in done] or [""]]}, fields=["name", "title", "icon", "color"])}
	return {
		"achievements": achievements.unseen(user),
		"challenges": [{"name": d.name, "xp": d.xp_awarded, **{k: info[d.challenge][k] for k in ("title", "icon", "color")}} for d in done if d.challenge in info],
	}


def mark_celebrated(user: str, achievement_names: list[str], participation_names: list[str]) -> None:
	achievements.mark_seen(user, achievement_names)
	for name in participation_names or []:
		if frappe.db.get_value(PARTICIPATION, name, "user") == user:
			frappe.db.set_value(PARTICIPATION, name, "celebrated", 1, update_modified=False)


def summary(user: str) -> dict:
	from atomic_streak.constants import PROFILE

	total = frappe.db.get_value(PROFILE, user, "xp") or 0
	return {**xp.level_progress(total), "achievements": achievements.list_for(user)}
