# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import flt

SOURCE_TYPES = ("LMS Course", "LMS Batch")


class LMSCreditEntry(Document):
	def validate(self):
		if self.source_type not in SOURCE_TYPES:
			frappe.throw(_("Credit can only come from a course or a batch."))
		if frappe.db.exists(
			"LMS Credit Entry",
			{
				"member": self.member,
				"source_type": self.source_type,
				"source": self.source,
				"name": ("!=", self.name),
			},
		):
			frappe.throw(
				_("{0} already has credit for {1}.").format(self.member_name or self.member, self.source)
			)


def award_credit(member: str, source_type: str, source: str):
	"""Credit `member` once with the source's credit_hours; a source without any credits nothing.

	shortcut: earned credit stays when progress later drops or a certificate is
	withdrawn; reverse it here if the ministry asks for that."""
	hours = flt(frappe.db.get_value(source_type, source, "credit_hours"))
	if hours <= 0 or frappe.db.exists(
		"LMS Credit Entry", {"member": member, "source_type": source_type, "source": source}
	):
		return
	# nosemgrep: lms-unjustified-ignore-permissions - the system awards credit; learners cannot write entries
	frappe.get_doc(
		{
			"doctype": "LMS Credit Entry",
			"member": member,
			"source_type": source_type,
			"source": source,
			"hours": hours,
		}
	).insert(ignore_permissions=True)


def total_credit_hours(member: str) -> float:
	entry = frappe.qb.DocType("LMS Credit Entry")
	total = frappe.qb.from_(entry).select(Sum(entry.hours)).where(entry.member == member).run()
	return flt(total[0][0]) if total else 0.0
