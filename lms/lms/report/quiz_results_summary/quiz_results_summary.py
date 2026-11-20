# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Avg, Count, Max, Min, Sum
from frappe.utils import add_days, flt, getdate

from lms.lms.dashboard.common import scored_quiz


def execute(filters=None):
	"""Per quiz: attempts, learners, the highest, lowest and average percentage, and the
	share of attempts that passed. Surveys and polls have no scores and are left out."""
	filters = frappe._dict(filters or {})
	submission = frappe.qb.DocType("LMS Quiz Submission")
	quiz = frappe.qb.DocType("LMS Quiz")
	passed = Case().when(submission.percentage >= submission.passing_percentage, 1).else_(0)
	query = (
		frappe.qb.from_(submission)
		.join(quiz)
		.on(quiz.name == submission.quiz)
		.select(
			submission.quiz,
			quiz.title.as_("quiz_title"),
			Count(submission.name).as_("attempts"),
			Count(submission.member).distinct().as_("learners"),
			Max(submission.percentage).as_("highest"),
			Min(submission.percentage).as_("lowest"),
			Avg(submission.percentage).as_("average"),
			Sum(passed).as_("passed"),
		)
		.where(
			scored_quiz(quiz)
			& submission.creation.between(getdate(filters.from_date), add_days(getdate(filters.to_date), 1))
		)
		.groupby(submission.quiz, quiz.title)
		.orderby(quiz.title)
	)
	if filters.course:
		query = query.where(submission.quiz.isin(course_quizzes(filters.course) or [""]))
	if filters.quiz:
		query = query.where(submission.quiz == filters.quiz)

	rows = query.run(as_dict=True)
	for row in rows:
		row.average = flt(row.average, 1)
		row.pass_rate = flt(100 * flt(row.passed) / row.attempts, 1) if row.attempts else 0
	return get_columns(), rows


def course_quizzes(course: str) -> list[str]:
	"""The quizzes the course's lessons place, resolved through its chapters: a submission's
	own `course` is a stale stamp that is mostly empty."""
	chapters = frappe.get_all("Course Chapter", filters={"course": course}, pluck="name")
	lessons = frappe.get_all("Course Lesson", filters={"chapter": ("in", chapters or [""])}, pluck="name")
	return frappe.get_all(
		"LMS Lesson Assessment",
		filters={
			"parenttype": "Course Lesson",
			"parent": ("in", lessons or [""]),
			"assessment_type": "LMS Quiz",
		},
		pluck="assessment_name",
		distinct=True,
	)


def get_columns():
	return [
		{"fieldname": "quiz", "fieldtype": "Link", "label": _("Quiz"), "options": "LMS Quiz", "width": 160},
		{"fieldname": "quiz_title", "fieldtype": "Data", "label": _("Quiz Title"), "width": 220},
		{"fieldname": "attempts", "fieldtype": "Int", "label": _("Attempts"), "width": 90},
		{"fieldname": "learners", "fieldtype": "Int", "label": _("Learners"), "width": 90},
		{"fieldname": "highest", "fieldtype": "Percent", "label": _("Highest"), "width": 90},
		{"fieldname": "lowest", "fieldtype": "Percent", "label": _("Lowest"), "width": 90},
		{"fieldname": "average", "fieldtype": "Percent", "label": _("Average"), "width": 90},
		{"fieldname": "pass_rate", "fieldtype": "Percent", "label": _("Passed"), "width": 90},
	]
