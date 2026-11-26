import json
from unittest.mock import patch

import frappe

from lms.lms.doctype.lms_quiz import lms_quiz
from lms.lms.doctype.lms_quiz.lms_quiz import submit_quiz
from lms.lms.test_helpers import BaseTestUtils


class TestShowScore(BaseTestUtils):
	"""A quiz that hides its score tells the learner whether they passed and nothing more."""

	def setUp(self):
		super().setUp()
		hash = frappe.generate_hash(length=6)
		instructor = self._create_user(f"ss-i-{hash}@example.com", "Ina", "Instr", ["Course Creator"]).name
		self.learner = self._create_user(f"ss-l-{hash}@example.com", "Lee", "Learner", ["LMS Student"]).name
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
		course = self._create_course(f"Score Course {hash}", instructor=instructor).name
		self._create_enrollment(self.learner, course)
		quiz = frappe.get_doc(
			{"doctype": "LMS Quiz", "title": f"Score Quiz {hash}", "passing_percentage": 50}
		)
		quiz.append("questions", {"question": self.question.name, "marks": 1})
		self.quiz = quiz.insert().name
		self._place_in_lesson(course, "LMS Quiz", self.quiz)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def answer(self):
		frappe.set_user(self.learner)
		try:
			return submit_quiz(
				self.quiz, json.dumps([{"question_name": self.question.name, "answer": ["4"]}])
			)
		finally:
			frappe.set_user("Administrator")

	def test_a_quiz_shows_its_score_by_default(self):
		result = self.answer()
		self.assertEqual((result["pass"], result["score"], result["percentage"]), (True, 1, 100))

	def test_a_hidden_score_leaves_only_the_verdict(self):
		frappe.db.set_value("LMS Quiz", self.quiz, "show_score", 0)
		result = self.answer()
		self.assertTrue(result["pass"])
		for key in ("score", "score_out_of", "percentage", "correct", "wrong"):
			self.assertNotIn(key, result)

	def test_grading_a_hidden_score_says_graded_without_the_marks(self):
		frappe.db.set_value("LMS Quiz", self.quiz, "show_score", 0)
		submission = frappe.get_doc("LMS Quiz Submission", self.answer()["submission"])
		submission.result[0].marks = 0
		with patch.object(lms_quiz, "send_quiz_email") as send:
			submission.save(ignore_permissions=True)
		args = send.call_args.args[4]
		self.assertFalse(args["show_score"])
		self.assertIsNone(args["score"])
		self.assertIsNone(args["percentage"])

		submission.result[0].marks = 1
		with patch.object(lms_quiz, "send_quiz_email"):
			submission.save(ignore_permissions=True)
		alert = frappe.get_last_doc("Notification Log", {"for_user": self.learner})
		self.assertIn("has been graded", alert.subject)
		self.assertNotIn("score", alert.subject)
