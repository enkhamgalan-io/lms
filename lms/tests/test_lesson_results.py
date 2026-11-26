import json

import frappe

from lms.lms.api import get_my_lesson_results
from lms.lms.doctype.lms_quiz.lms_quiz import submit_quiz
from lms.lms.test_helpers import BaseTestUtils


class TestLessonResults(BaseTestUtils):
	"""A learner sees, on each lesson, whether it is complete and how they did on its quizzes."""

	def setUp(self):
		super().setUp()
		hash = frappe.generate_hash(length=6)
		instructor = self._create_user(f"lr-i-{hash}@example.com", "Ina", "Instr", ["Course Creator"]).name
		self.learner = self._create_user(f"lr-l-{hash}@example.com", "Lee", "Learner", ["LMS Student"]).name
		self.outsider = self._create_user(f"lr-o-{hash}@example.com", "Out", "Sider", ["LMS Student"]).name
		self.question = frappe.get_doc(
			{
				"doctype": "LMS Question",
				"question": f"Two plus two {hash}?",
				"type": "Choices",
				"option_1": "4",
				"is_correct_1": 1,
				"option_2": "5",
			}
		).insert()
		self.course = self._create_course(f"Results Course {hash}", instructor=instructor).name
		self._create_enrollment(self.learner, self.course)
		quiz = frappe.get_doc(
			{"doctype": "LMS Quiz", "title": f"Results Quiz {hash}", "passing_percentage": 50}
		)
		quiz.append("questions", {"question": self.question.name, "marks": 1})
		self.quiz = quiz.insert().name
		self.lesson = self._place_in_lesson(self.course, "LMS Quiz", self.quiz).name

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def results(self, user):
		frappe.set_user(user)
		try:
			return get_my_lesson_results(self.lesson)
		finally:
			frappe.set_user("Administrator")

	def test_an_untaken_quiz_shows_as_not_attempted(self):
		results = self.results(self.learner)
		self.assertFalse(results["completed"])
		self.assertEqual(
			[(row["name"], row["status"], row["score"]) for row in results["assessments"]],
			[(self.quiz, "not_attempted", None)],
		)

	def test_a_taken_quiz_shows_the_verdict_score_and_attempts(self):
		frappe.set_user(self.learner)
		submit_quiz(self.quiz, json.dumps([{"question_name": self.question.name, "answer": ["4"]}]))
		row = self.results(self.learner)["assessments"][0]
		self.assertEqual((row["status"], row["score"], row["attempts"]), ("passed", 100, 1))

	def test_a_quiz_that_hides_its_score_keeps_only_the_verdict(self):
		frappe.db.set_value("LMS Quiz", self.quiz, "show_score", 0)
		frappe.set_user(self.learner)
		submit_quiz(self.quiz, json.dumps([{"question_name": self.question.name, "answer": ["4"]}]))
		row = self.results(self.learner)["assessments"][0]
		self.assertEqual((row["status"], row["score"]), ("passed", None))

	def test_a_completed_lesson_says_so(self):
		frappe.get_doc(
			{
				"doctype": "LMS Course Progress",
				"member": self.learner,
				"course": self.course,
				"lesson": self.lesson,
				"status": "Complete",
			}
		).insert(ignore_permissions=True)
		self.assertTrue(self.results(self.learner)["completed"])

	def test_someone_not_in_the_course_is_refused(self):
		with self.assertRaises(frappe.PermissionError):
			self.results(self.outsider)

	def test_a_guest_gets_nothing(self):
		self.assertEqual(self.results("Guest"), {"completed": False, "assessments": []})
