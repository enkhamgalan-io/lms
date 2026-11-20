from unittest.mock import patch

import frappe
from frappe.utils import add_days, nowdate

from lms.lms.api import record_lesson_view
from lms.lms.dashboard.course import get_course_views
from lms.lms.test_helpers import BaseTestUtils


class TestLessonViews(BaseTestUtils):
	"""Each opening of a lesson by a learner is counted, one row a day, and the course
	dashboard sums the rows per day or month and ranks the lessons."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		hash = frappe.generate_hash(length=6)
		cls.instructor = cls._create_user(f"lv-i-{hash}@example.com", "Ina", "Instr", ["Course Creator"]).name
		cls.learner = cls._create_user(f"lv-l-{hash}@example.com", "Lee", "Learner", ["LMS Student"]).name
		cls.other = cls._create_user(f"lv-o-{hash}@example.com", "Oli", "Other", ["LMS Student"]).name
		cls.stranger = cls._create_user(f"lv-s-{hash}@example.com", "Sam", "Stranger", ["LMS Student"]).name
		cls.course = cls._create_course(f"Views Course {hash}", instructor=cls.instructor).name
		chapter = cls._create_chapter(f"Views Chapter {hash}", cls.course)
		cls.first = cls._create_lesson(f"Views First {hash}", chapter.name, cls.course).name
		cls.second = cls._create_lesson(f"Views Second {hash}", chapter.name, cls.course).name
		cls._create_enrollment(cls.learner, cls.course)
		cls._create_enrollment(cls.other, cls.course)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def _open(self, user, lesson, day=None):
		frappe.set_user(user)
		with patch("lms.lms.doctype.lms_lesson_view.lms_lesson_view.today", lambda: day or nowdate()):
			record_lesson_view(lesson)
		frappe.set_user("Administrator")

	def _rows(self, lesson):
		return frappe.get_all("LMS Lesson View", {"lesson": lesson}, ["member", "date", "count"])

	def test_openings_on_one_day_share_a_row(self):
		self._open(self.learner, self.first)
		self._open(self.learner, self.first)
		self._open(self.learner, self.first, add_days(nowdate(), -1))
		rows = {str(row.date): row.count for row in self._rows(self.first) if row.member == self.learner}
		self.assertEqual(rows, {nowdate(): 2, add_days(nowdate(), -1): 1})

	def test_staff_and_outsiders_are_not_counted(self):
		self._open(self.instructor, self.second)
		self.assertEqual(self._rows(self.second), [])

		frappe.set_user(self.stranger)
		with self.assertRaises(frappe.PermissionError):
			record_lesson_view(self.second)

	def test_the_dashboard_sums_per_day_and_ranks_the_lessons(self):
		self._open(self.learner, self.first)
		self._open(self.learner, self.first)
		self._open(self.other, self.first)
		self._open(self.other, self.second)

		frappe.set_user(self.instructor)
		views = get_course_views(self.course, "day")
		self.assertEqual(len(views["series"]), 30)
		self.assertEqual(views["series"][-1], {"period": nowdate(), "views": 4, "viewers": 2})
		self.assertEqual(
			[(row["lesson"], row["views"], row["viewers"]) for row in views["lessons"]],
			[(self.first, 3, 2), (self.second, 1, 1)],
		)

		months = get_course_views(self.course, "month")["series"]
		self.assertEqual(len(months), 12)
		self.assertEqual(months[-1]["views"], 4)

	def test_only_the_courses_staff_see_its_views(self):
		frappe.set_user(self.learner)
		with self.assertRaises(frappe.PermissionError):
			get_course_views(self.course)
