# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Count, DateFormat, Sum
from frappe.utils import getdate

PERIOD_FORMAT = {"Day": "%Y-%m-%d", "Month": "%Y-%m"}


def execute(filters=None):
	"""Lesson opens per day or month and lesson, from LMS Lesson View, busiest first within a period."""
	filters = frappe._dict(filters or {})
	view = frappe.qb.DocType("LMS Lesson View")
	lesson = frappe.qb.DocType("Course Lesson")
	course = frappe.qb.DocType("LMS Course")
	period = DateFormat(view.date, PERIOD_FORMAT.get(filters.group_by, PERIOD_FORMAT["Day"]))
	query = (
		frappe.qb.from_(view)
		.left_join(lesson)
		.on(lesson.name == view.lesson)
		.left_join(course)
		.on(course.name == view.course)
		.select(
			period.as_("period"),
			view.course,
			course.title.as_("course_title"),
			view.lesson,
			lesson.title.as_("lesson_title"),
			Sum(view["count"]).as_("views"),
			Count(view.member).distinct().as_("learners"),
		)
		.where(view.date.between(getdate(filters.from_date), getdate(filters.to_date)))
		.groupby(period, view.course, view.lesson)
		.orderby(period, order=frappe.qb.desc)
		.orderby(Sum(view["count"]), order=frappe.qb.desc)
	)
	if filters.course:
		query = query.where(view.course == filters.course)
	if filters.member:
		query = query.where(view.member == filters.member)
	return get_columns(), query.run(as_dict=True)


def get_columns():
	return [
		{"fieldname": "period", "fieldtype": "Data", "label": _("Period"), "width": 110},
		{
			"fieldname": "course",
			"fieldtype": "Link",
			"label": _("Course"),
			"options": "LMS Course",
			"width": 160,
		},
		{"fieldname": "course_title", "fieldtype": "Data", "label": _("Course Title"), "width": 200},
		{
			"fieldname": "lesson",
			"fieldtype": "Link",
			"label": _("Lesson"),
			"options": "Course Lesson",
			"width": 160,
		},
		{"fieldname": "lesson_title", "fieldtype": "Data", "label": _("Lesson Title"), "width": 220},
		{"fieldname": "views", "fieldtype": "Int", "label": _("Views"), "width": 90},
		{"fieldname": "learners", "fieldtype": "Int", "label": _("Learners"), "width": 90},
	]
