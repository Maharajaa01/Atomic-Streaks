app_name = "atomic_streak"
app_title = "Atomic Streak"
app_publisher = "Maharaja"
app_description = "This App is used to Habbits Tracking "
app_email = "vijaymaharajan38@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "atomic_streak",
# 		"logo": "/assets/atomic_streak/logo.png",
# 		"title": "Atomic Streak",
# 		"route": "/atomic_streak",
# 		"has_permission": "atomic_streak.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/atomic_streak/css/atomic_streak.css"
# app_include_js = "/assets/atomic_streak/js/atomic_streak.js"

# include js, css files in header of web template
# web_include_css = "/assets/atomic_streak/css/atomic_streak.css"
# web_include_js = "/assets/atomic_streak/js/atomic_streak.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "atomic_streak/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "atomic_streak/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "atomic_streak.utils.jinja_methods",
# 	"filters": "atomic_streak.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "atomic_streak.install.before_install"
# after_install = "atomic_streak.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "atomic_streak.uninstall.before_uninstall"
# after_uninstall = "atomic_streak.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "atomic_streak.utils.before_app_install"
# after_app_install = "atomic_streak.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "atomic_streak.utils.before_app_uninstall"
# after_app_uninstall = "atomic_streak.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "atomic_streak.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
	# reminders are matched to each user's own timezone, so this runs often and checks who is due
	"cron": {"*/5 * * * *": ["atomic_streak.services.reminders.run"]},
}

# scheduler_events = {
# 	"all": [
# 		"atomic_streak.tasks.all"
# 	],
# 	"daily": [
# 		"atomic_streak.tasks.daily"
# 	],
# 	"hourly": [
# 		"atomic_streak.tasks.hourly"
# 	],
# 	"weekly": [
# 		"atomic_streak.tasks.weekly"
# 	],
# 	"monthly": [
# 		"atomic_streak.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "atomic_streak.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "atomic_streak.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "atomic_streak.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["atomic_streak.utils.before_request"]
# after_request = ["atomic_streak.utils.after_request"]

# Job Events
# ----------
# before_job = ["atomic_streak.utils.before_job"]
# after_job = ["atomic_streak.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"atomic_streak.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


# ------------------------------------------------------------------------- Atomic Streak
after_install = "atomic_streak.setup.install.after_install"
after_migrate = "atomic_streak.setup.install.after_migrate"

doc_events = {
	"User": {
		"on_trash": "atomic_streak.setup.cleanup.on_user_trash",
	},
}

after_request = ["atomic_streak.http.after_request"]

# The Vue app lives at /atomic-streak (Frappe's own /login stays untouched for ERP staff).
website_route_rules = [
	{"from_route": "/atomic-streak", "to_route": "atomic_streak_app"},
	{"from_route": "/atomic-streak/<path:app_path>", "to_route": "atomic_streak_app"},
]
