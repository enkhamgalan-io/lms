import json

import frappe
from frappe.utils import add_days, getdate, nowdate

from lms.lms.dashboard.course import set_course_access
from lms.lms.permissions import can_access_lesson, can_access_quiz
from lms.lms.test_helpers import BaseTestUtils
from lms.lms.utils import get_membership, has_active_enrollment


class TestCourseAccessDays(BaseTestUtils):
	"""A course with access_days opens to a learner for that many days from enrolling.
	After that its lessons and quizzes close until the course's staff extend it."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		hash = frappe.generate_hash(length=6)
		cls.instructor = cls._create_user(f"ad-i-{hash}@example.com", "Ida", "Instr", ["Course Creator"]).name
		cls.learner = cls._create_user(f"ad-l-{hash}@example.com", "Lee", "Learner", ["LMS Student"]).name
		cls.other = cls._create_user(f"ad-o-{hash}@example.com", "Oli", "Other", ["LMS Student"]).name

		question = frappe.get_doc(
			{
				"doctype": "LMS Question",
				"question": f"Access {hash}?",
				"type": "Choices",
				"option_1": "Yes",
				"is_correct_1": 1,
				"option_2": "No",
			}
		).insert()
		quiz = frappe.get_doc(
			{"doctype": "LMS Quiz", "title": f"Access Quiz {hash}", "passing_percentage": 50}
		)
		quiz.append("questions", {"question": question.name, "marks": 1})
		cls.quiz = quiz.insert().name

		course = cls._create_course(f"Access Course {hash}", instructor=cls.instructor)
		course.access_days = 10
		course.save()
		cls.course = course.name
		chapter = cls._create_chapter(f"Access Chapter {hash}", cls.course)
		content = json.dumps(
			{"blocks": [{"id": "q", "type": "quiz", "data": {"quiz": cls.quiz}}], "version": "2.29.0"}
		)
		cls.lesson = cls._create_lesson(f"Access Lesson {hash}", chapter.name, cls.course, content).name
		cls.open_course = cls._create_course(f"Open Course {hash}", instructor=cls.instructor).name

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def _enroll_self(self, user, course):
		frappe.set_user(user)
		return frappe.get_doc({"doctype": "LMS Enrollment", "course": course, "member": user}).insert()

	def _expire(self, enrollment):
		frappe.db.set_value("LMS Enrollment", enrollment, "valid_until", add_days(nowdate(), -1))

	def test_enrolling_starts_the_clock(self):
		enrollment = self._enroll_self(self.learner, self.course)
		self.assertEqual(getdate(enrollment.valid_until), getdate(add_days(nowdate(), 10)))

		self.assertIsNone(self._enroll_self(self.learner, self.open_course).valid_until)

	def test_a_learner_cannot_move_their_own_end(self):
		enrollment = self._enroll_self(self.other, self.course)
		enrollment.valid_until = add_days(nowdate(), 400)
		enrollment.save()
		self.assertEqual(getdate(enrollment.reload().valid_until), getdate(add_days(nowdate(), 10)))

	def test_lessons_and_quizzes_close_when_access_ends(self):
		enrollment = self._enroll_self(self.learner, self.course).name
		self.assertTrue(can_access_lesson(self.lesson, user=self.learner))
		self.assertTrue(can_access_quiz(self.quiz, user=self.learner))

		self._expire(enrollment)
		self.assertFalse(has_active_enrollment(self.course, self.learner))
		self.assertFalse(can_access_lesson(self.lesson, user=self.learner))
		self.assertFalse(can_access_quiz(self.quiz, user=self.learner))
		# Still enrolled, so the course page says why rather than offering to enroll.
		self.assertTrue(get_membership(self.course, self.learner).access_expired)

	def test_staff_extend_access_and_learners_cannot(self):
		enrollment = self._enroll_self(self.learner, self.course).name
		self._expire(enrollment)

		with self.assertRaises(frappe.PermissionError):
			set_course_access(self.course, enrollment, add_days(nowdate(), 30))

		frappe.set_user(self.instructor)
		set_course_access(self.course, enrollment, add_days(nowdate(), 30))
		self.assertTrue(can_access_lesson(self.lesson, user=self.learner))

		set_course_access(self.course, enrollment, None)
		self.assertIsNone(frappe.db.get_value("LMS Enrollment", enrollment, "valid_until"))
