# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today


class LMSLessonView(Document):
	pass


def record_view(member: str, course: str, lesson: str) -> None:
	"""Count one opening of `lesson` by `member` today, in the day's single row."""
	date = today()
	name = frappe.db.get_value("LMS Lesson View", {"member": member, "lesson": lesson, "date": date})
	if name:
		View = frappe.qb.DocType("LMS Lesson View")
		frappe.qb.update(View).set(View["count"], View["count"] + 1).where(View.name == name).run()
		return
	# shortcut: two first openings in the same instant can each insert a row; every reader
	# sums `count`, so totals stay right. Add a unique (member, lesson, date) index to fold them.
	frappe.get_doc(
		{"doctype": "LMS Lesson View", "member": member, "course": course, "lesson": lesson, "date": date}
	).insert(ignore_permissions=True)
