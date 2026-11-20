# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, getdate


def execute(filters=None):
	"""Every login and logout in the period, newest first, from Frappe's Activity Log."""
	filters = frappe._dict(filters or {})
	conditions = {
		"operation": ("in", ["Login", "Logout"]),
		"creation": ("between", [getdate(filters.from_date), add_days(getdate(filters.to_date), 1)]),
	}
	if filters.user:
		conditions["user"] = filters.user
	rows = frappe.get_all(
		"Activity Log",
		filters=conditions,
		fields=["creation", "user", "full_name", "operation", "status", "ip_address"],
		order_by="creation desc",
	)
	return get_columns(), rows


def get_columns():
	return [
		{"fieldname": "creation", "fieldtype": "Datetime", "label": _("Time"), "width": 180},
		{"fieldname": "user", "fieldtype": "Link", "label": _("User"), "options": "User", "width": 220},
		{"fieldname": "full_name", "fieldtype": "Data", "label": _("Full Name"), "width": 180},
		{"fieldname": "operation", "fieldtype": "Data", "label": _("Operation"), "width": 100},
		{"fieldname": "status", "fieldtype": "Data", "label": _("Status"), "width": 100},
		{"fieldname": "ip_address", "fieldtype": "Data", "label": _("IP Address"), "width": 140},
	]
