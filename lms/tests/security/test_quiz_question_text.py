import json

import frappe
from frappe.client import get as client_get
from frappe.client import get_list as client_get_list

from lms.lms.test_helpers import BaseTestUtils
from lms.lms.utils import get_quiz_with_questions


class TestQuizQuestionText(BaseTestUtils):
	"""A learner reads a quiz's questions only as their attempt draws them. The REST read
	of the quiz used to hand them every row's question text, the whole pool included."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		hash = frappe.generate_hash(length=6)
		cls.instructor = cls._create_user(f"qt-i-{hash}@example.com", "Ina", "Instr", ["Course Creator"]).name
		cls.learner = cls._create_user(f"qt-l-{hash}@example.com", "Lee", "Learner", ["LMS Student"]).name
		quiz = cls._create_quiz(cls._create_quiz_questions()[:2], title=f"Text Quiz {hash}")
		cls.quiz = quiz.name
		course = cls._create_course(f"Text Course {hash}", instructor=cls.instructor).name
		chapter = cls._create_chapter(f"Text Chapter {hash}", course)
		content = json.dumps(
			{"blocks": [{"id": "q", "type": "quiz", "data": {"quiz": cls.quiz}}], "version": "2.29.0"}
		)
		cls._create_lesson(f"Text Lesson {hash}", chapter.name, course, content)
		cls._create_enrollment(cls.learner, course)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_the_rest_read_leaves_the_questions_out_for_a_learner(self):
		frappe.set_user(self.learner)
		doc = client_get("LMS Quiz", self.quiz)
		self.assertTrue(doc.get("title"))
		self.assertFalse(doc.get("questions"))

	def test_the_question_rows_cannot_be_listed_on_their_own(self):
		frappe.set_user(self.learner)
		try:
			rows = client_get_list(
				"LMS Quiz Question",
				fields=["question_detail"],
				filters={"parent": self.quiz},
				parent="LMS Quiz",
			)
		except frappe.PermissionError:
			rows = []
		self.assertEqual([row for row in rows if row.get("question_detail")], [])

	def test_staff_still_read_and_the_attempt_still_draws_them(self):
		frappe.set_user(self.instructor)
		self.assertEqual(len(client_get("LMS Quiz", self.quiz)["questions"]), 2)

		frappe.set_user(self.learner)
		self.assertEqual(len(get_quiz_with_questions(self.quiz)["quiz"]["questions"]), 2)
