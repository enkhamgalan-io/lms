# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.nestedset import NestedSet

from lms.lms.permissions import ORGANIZATION_MANAGER_ROLE


class LMSOrganization(NestedSet):
	nsm_parent_field = "parent_lms_organization"

	def on_update(self):
		super().on_update()
		before = self.get_doc_before_save()
		previous = {row.user for row in before.managers} if before else set()
		for user in previous | {row.user for row in self.managers}:
			sync_manager_role(user)

	def after_delete(self):
		for row in self.managers:
			sync_manager_role(row.user)


def sync_manager_role(user: str):
	"""The managers table is what makes someone an Organization Manager; the role follows it."""
	manages = frappe.db.exists("LMS Organization Manager", {"user": user, "parenttype": "LMS Organization"})
	holds = frappe.db.exists(
		"Has Role", {"parent": user, "parenttype": "User", "role": ORGANIZATION_MANAGER_ROLE}
	)
	if manages and not holds:
		frappe.get_doc(
			{
				"doctype": "Has Role",
				"parent": user,
				"parenttype": "User",
				"parentfield": "roles",
				"role": ORGANIZATION_MANAGER_ROLE,
			}
		).insert(ignore_permissions=True)
	elif holds and not manages:
		frappe.db.delete(
			"Has Role", {"parent": user, "parenttype": "User", "role": ORGANIZATION_MANAGER_ROLE}
		)
	frappe.clear_cache(user=user)
