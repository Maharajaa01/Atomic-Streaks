"""Profiles created before the fix got their sign-up time as the daily reminder time (Frappe
fills empty Time fields with "now" on insert). Reset exactly those to the intended 08:00.

A time that differs from the creation time by more than a minute was chosen by the person,
so it is left alone.
"""

import frappe


def execute():
	frappe.db.sql(
		"""update `tabAtomic User Profile`
		set daily_reminder_time = '08:00:00'
		where daily_reminder_time is not null
		and abs(time_to_sec(timediff(daily_reminder_time, time(creation)))) <= 60"""
	)
