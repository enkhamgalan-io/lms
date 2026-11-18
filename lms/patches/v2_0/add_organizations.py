import frappe

from lms.install import create_lms_custom_fields, create_organization_manager_role, create_role


def execute():
	"""Organizations: the role their managers hold, its read on User, and the User fields
	that place a person in an organization."""
	frappe.reload_doc("lms", "doctype", "lms_organization_manager")
	frappe.reload_doc("lms", "doctype", "lms_organization")
	create_organization_manager_role()
	create_role("User", "Organization Manager", 0)
	create_lms_custom_fields()
