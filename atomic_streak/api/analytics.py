"""Insights endpoint (signed-in app user, own data only)."""

import frappe

from atomic_streak.api.habit import _user
from atomic_streak.services import analytics


@frappe.whitelist(methods=["GET"])
def get_dashboard(days: int = 30) -> dict:
	return analytics.dashboard(_user(), days)
