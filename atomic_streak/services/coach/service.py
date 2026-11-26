"""Coach conversations: stored per user, answered by Claude when enabled, else by the rules."""

import frappe
from frappe import _
from frappe.utils import cint, getdate, now_datetime

from atomic_streak.constants import CONVERSATION, SETTINGS
from atomic_streak.services.coach import context, providers, rules
from atomic_streak.utils import clean_text

MAX_MESSAGE = 1500
HISTORY_TURNS = 12
MAX_CONVERSATIONS = 50
MAX_MESSAGES = 200  # per conversation (100 exchanges); a longer chat continues in a new one


def ai_status() -> dict:
	settings = frappe.get_cached_doc(SETTINGS)
	enabled = bool(providers.get_provider())
	return {"ai": enabled, "model": settings.ai_model if enabled else None, "daily_limit": cint(settings.ai_daily_message_limit) or 30}


def _owned(user: str, name: str):
	if not name or frappe.db.get_value(CONVERSATION, name, "user") != user:
		frappe.throw(_("Conversation not found."), frappe.DoesNotExistError)
	return frappe.get_doc(CONVERSATION, name)


def serialize(doc) -> dict:
	return {
		"name": doc.name,
		"title": doc.title,
		"last_message_at": str(doc.last_message_at) if doc.last_message_at else None,
		"messages": [
			{"role": m.role, "content": m.content, "created_at": str(m.created_at), "provider": m.provider}
			for m in doc.messages
		],
	}


def list_conversations(user: str) -> list[dict]:
	return frappe.get_all(
		CONVERSATION,
		filters={"user": user, "is_archived": 0},
		fields=["name", "title", "last_message_at"],
		order_by="last_message_at desc",
		limit=20,
	)


def get(user: str, name: str) -> dict:
	return serialize(_owned(user, name))


def _ai_messages_today(user: str) -> int:
	today = getdate(now_datetime())
	return cint(
		frappe.db.sql(
			"""select count(*) from `tabAtomic Coach Message` m
			join `tabAtomic Coach Conversation` c on c.name = m.parent
			where c.user = %s and m.role = 'user' and m.provider != 'rules' and date(m.created_at) = %s""",
			(user, today),
		)[0][0]
	)


def chat(user: str, message: str, conversation: str | None = None) -> dict:
	message = clean_text(message, _("Message"), MAX_MESSAGE, required=True)
	doc = _owned(user, conversation) if conversation else None
	if doc and len(doc.messages) + 2 > MAX_MESSAGES:
		doc = None  # full: carry on in a fresh conversation (the reply says which)
	if not doc:
		if frappe.db.count(CONVERSATION, {"user": user}) >= MAX_CONVERSATIONS:
			oldest = frappe.get_all(CONVERSATION, filters={"user": user}, order_by="last_message_at asc", limit=1, pluck="name")
			frappe.delete_doc(CONVERSATION, oldest[0], ignore_permissions=True)
		doc = frappe.new_doc(CONVERSATION)
		doc.user = user
		doc.title = message[:60]

	snap = context.snapshot(user)
	provider = providers.get_provider()
	status = ai_status()
	answer, suggestions, used, note = None, [], "rules", None

	if provider and _ai_messages_today(user) >= status["daily_limit"]:
		note = _("You've reached today's AI coach limit. Here's a tip from the built-in coach instead.")
		provider = None
	if provider:
		history = [{"role": m.role, "content": m.content} for m in doc.messages][-(HISTORY_TURNS * 2) :]
		history.append({"role": "user", "content": message})
		while history and history[0]["role"] != "user":
			history.pop(0)  # the API needs the first message to be the user's
		try:
			out = provider.reply(history, context.as_text(snap))
			answer, used = out["text"], out["provider"]
		except providers.ProviderUnavailable:
			note = _("The AI coach is unavailable right now. Here's a tip from the built-in coach.")
	# suggestion cards come from the curated catalogue either way (one tap to add)
	rule = rules.reply(message, snap)
	if answer is None:
		answer = rule["text"]
	suggestions = rule["suggestions"]

	now = now_datetime()
	doc.append("messages", {"role": "user", "content": message, "created_at": now, "provider": used})
	doc.append("messages", {"role": "assistant", "content": answer, "created_at": now, "provider": used})
	doc.last_message_at = now
	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)
	return {"conversation": doc.name, "reply": answer, "provider": used, "suggestions": suggestions, "note": note}


def delete(user: str, name: str) -> None:
	_owned(user, name)
	frappe.delete_doc(CONVERSATION, name, ignore_permissions=True)


def weekly_summary(user: str) -> dict:
	return {"text": rules.weekly_summary(context.snapshot(user))}


def suggestions_for(goal: str | None) -> list[dict]:
	from atomic_streak.services.coach.catalog import goals_in

	return rules._pick_suggestions(goals_in(goal or ""), limit=6)


