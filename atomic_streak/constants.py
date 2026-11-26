"""Role names, DocType names and shared values for Atomic Streak.

Role names start with "Atomic Streak" so they cannot collide with ERPNext/HRMS/CRM roles that
live on the same site.
"""

ROLE_USER = "Atomic Streak User"  # app users: website-only, no Desk, no direct DocType access
ROLE_MANAGER = "Atomic Streak Manager"  # staff who curate categories, challenges, achievements

APP_ROUTE = "/atomic-streak"

PROFILE = "Atomic User Profile"
HABIT = "Atomic Habit"
CATEGORY = "Atomic Habit Category"
COMPLETION = "Atomic Habit Completion"
ROUTINE = "Atomic Habit Routine"
CHALLENGE = "Atomic Challenge"
PARTICIPATION = "Atomic Challenge Participation"
ACHIEVEMENT = "Atomic Achievement"
USER_ACHIEVEMENT = "Atomic User Achievement"
SUBSCRIPTION = "Atomic Notification Subscription"
CONVERSATION = "Atomic Coach Conversation"
SETTINGS = "Atomic Streak Settings"
PLAN_TASK = "Atomic Plan Task"

# Every DocType whose rows belong to one user (a `user` Link field). Used by the ownership
# mixin, the delete-user cleanup and the isolation tests.
USER_OWNED = (
	PROFILE,
	HABIT,
	COMPLETION,
	ROUTINE,
	PARTICIPATION,
	USER_ACHIEVEMENT,
	SUBSCRIPTION,
	CONVERSATION,
	PLAN_TASK,
)

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


class HabitType:
	BUILD = "Build"
	BREAK = "Break"
	ONE_TIME = "One-time"


class Frequency:
	DAILY = "Daily"
	SPECIFIC_DAYS = "Specific Days"
	EVERY_N_DAYS = "Every N Days"


class HabitStatus:
	ACTIVE = "Active"
	PAUSED = "Paused"
	ARCHIVED = "Archived"
	COMPLETED = "Completed"


class CompletionStatus:
	COMPLETED = "Completed"
	PARTIAL = "Partial"


class ParticipationStatus:
	ACTIVE = "Active"
	COMPLETED = "Completed"
	FAILED = "Failed"
	ABANDONED = "Abandoned"


MAX_INTERVAL_DAYS = 365
MAX_DAILY_TARGET = 100_000
