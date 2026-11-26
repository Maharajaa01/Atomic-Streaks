"""Response headers for the Atomic Streak app.

Habit data must never sit in a shared or browser HTTP cache, so every Atomic Streak API response
and the session-bound app page are private + no-store. The service worker script is revalidated
on every load so new builds roll out promptly.
"""

API_PREFIX = "/api/method/atomic_streak."
APP = "/atomic-streak"


def after_request(response, request):
	path = request.path or ""
	if path.startswith(API_PREFIX) or path == APP or path.startswith(APP + "/"):
		response.headers["Cache-Control"] = "private, no-store, max-age=0"
		response.headers["Pragma"] = "no-cache"
		response.headers["X-Content-Type-Options"] = "nosniff"
	elif path == "/atomic_streak_sw.js":
		response.headers["Cache-Control"] = "no-cache, max-age=0"
		response.headers["Service-Worker-Allowed"] = APP
	return response
