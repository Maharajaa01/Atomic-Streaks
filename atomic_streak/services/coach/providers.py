"""AI providers for the coach. Modular: add a class with `reply()` and register it.

Keys live in Atomic Streak Settings (Password field) and are only ever used here, on the
server. Nothing is sent anywhere unless an administrator switches the AI coach on.
"""

import frappe

from atomic_streak.constants import SETTINGS

SYSTEM_PROMPT = """You are the habit coach inside Atomic Streak, a habit-tracking app built on the ideas in Atomic Habits.

How you help:
- Suggest small, specific habits that fit the person's goals. Prefer tiny versions (two minutes, two pages) they can do on a bad day.
- When a habit keeps slipping, make it easier: shrink it, attach it to an existing routine ("After I ..., I will ..."), or change the time.
- Use the progress data you are given. Mention real numbers when they help, and celebrate comebacks after missed days.
- Be warm and direct. Never shame or guilt the person about missed days.

Style: plain text, no markdown headings or tables, under 120 words unless they ask for more. Use the person's first name occasionally.
Stay on habits, routines, motivation and wellbeing. For medical, mental-health crisis or financial-advice questions, encourage them to speak with a qualified professional."""

# Models that accept the server-side refusal fallback (on others it is left off).
FALLBACK_MODELS = {"claude-fable-5-2", "claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}


class ProviderUnavailable(Exception):
	"""The provider couldn't answer (not configured, network, rate limit...). Fall back to rules."""


class AnthropicProvider:
	label = "Claude"

	def __init__(self, api_key: str, model: str):
		self.api_key = api_key
		self.model = model

	def reply(self, history: list[dict], context_text: str) -> dict:
		import anthropic

		client = anthropic.Anthropic(api_key=self.api_key, timeout=60.0, max_retries=2)
		params = {
			"model": self.model,
			"max_tokens": 16000,
			# stable instructions first (cached), the user's data after the breakpoint
			"system": [
				{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
				{"type": "text", "text": f"The person's progress data:\n{context_text}"},
			],
			"messages": history,
			"output_config": {"effort": "low"},  # chat: short, warm answers
		}
		if self.model in FALLBACK_MODELS:
			# on a policy decline the API re-runs the request on a fallback model in the same call
			params["betas"] = ["server-side-fallback-2026-07-01"]
			params["fallbacks"] = "default"
		try:
			response = client.beta.messages.create(**params)
		except anthropic.AuthenticationError:
			frappe.log_error(title="Atomic Streak coach: invalid API key")
			raise ProviderUnavailable("auth")
		except anthropic.PermissionDeniedError:
			frappe.log_error(title="Atomic Streak coach: API key lacks permission")
			raise ProviderUnavailable("permission")
		except anthropic.NotFoundError:
			frappe.log_error(title=f"Atomic Streak coach: model not found ({self.model})")
			raise ProviderUnavailable("model")
		except anthropic.BadRequestError as e:
			frappe.log_error(title="Atomic Streak coach: bad request", message=str(e.message))
			raise ProviderUnavailable("bad_request")
		except anthropic.RateLimitError:
			raise ProviderUnavailable("rate_limited")
		except anthropic.APIStatusError as e:
			frappe.log_error(title=f"Atomic Streak coach: API error {e.status_code}", message=str(e.message))
			raise ProviderUnavailable("api_error")
		except anthropic.APIConnectionError:
			raise ProviderUnavailable("network")

		if response.stop_reason == "refusal":
			return {
				"text": "That's outside what I can help with here. I'm happy to talk about your habits, routines or motivation.",
				"provider": self.model,
			}
		text = "".join(block.text for block in response.content if block.type == "text").strip()
		if not text:
			raise ProviderUnavailable("empty")
		return {"text": text, "provider": response.model or self.model}


def get_provider():
	"""The configured provider, or None when the AI coach is off (the rules coach answers)."""
	settings = frappe.get_cached_doc(SETTINGS)
	if not settings.ai_enabled:
		return None
	key = settings.get_password("ai_api_key", raise_exception=False)
	if not key:
		return None
	if (settings.ai_provider or "Anthropic") == "Anthropic":
		return AnthropicProvider(key.strip(), (settings.ai_model or "claude-opus-5-5").strip())
	return None
