import json
from unittest.mock import patch

import frappe

from lms.lms.doctype.lms_quiz import lms_quiz
from lms.lms.doctype.lms_quiz.lms_quiz import remove_from_quiz, submit_quiz
from lms.lms.doctype.lms_quiz_submission.lms_quiz_submission import MaximumAttemptsExceededError
from lms.lms.test_helpers import BaseTestUtils


class TestQuizRemoval(BaseTestUtils):
	"""Staff can end a learner's attempt; it is saved as removed, with no marks, and the
	learner's open screen is told to close."""

	def setUp(self):
		super().setUp()
		hash = frappe.generate_hash(length=6)
		self.instructor = self._create_user(
			f"qr-i-{hash}@example.com", "Ina", "Instr", ["Course Creator"]
		).name
		self.learner = self._create_user(f"qr-l-{hash}@example.com", "Lee", "Learner", ["LMS Student"]).name
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
		course = self._create_course(f"Removal Course {hash}", instructor=self.instructor).name
		self._create_enrollment(self.learner, course)
		quiz = frappe.get_doc(
			{
				"doctype": "LMS Quiz",
				"title": f"Removal Quiz {hash}",
				"passing_percentage": 50,
				"max_attempts": 2,
			}
		)
		quiz.append("questions", {"question": self.question.name, "marks": 1})
		self.quiz = quiz.insert().name
		self._place_in_lesson(course, "LMS Quiz", self.quiz)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def remove(self, as_user):
		frappe.set_user(as_user)
		try:
			with patch.object(frappe, "publish_realtime") as publish:
				name = remove_from_quiz(self.quiz, self.learner)
			return name, publish
		finally:
			frappe.set_user("Administrator")

	def test_the_instructor_removes_a_learner_with_no_marks(self):
		frappe.cache.set_value(lms_quiz._session_key(self.quiz, self.learner), "token")
		name, publish = self.remove(self.instructor)
		submission = frappe.get_doc("LMS Quiz Submission", name)
		self.assertEqual(
			(submission.member, submission.submission_reason, submission.score),
			(self.learner, "removed_by_admin", 0),
		)
		publish.assert_any_call("quiz_removed", {"quiz": self.quiz}, user=self.learner, after_commit=True)
		self.assertIsNone(frappe.cache.get_value(lms_quiz._session_key(self.quiz, self.learner)))

	def test_a_learner_cannot_remove_anyone(self):
		with self.assertRaises(frappe.PermissionError):
			self.remove(self.learner)

	def test_a_learner_cannot_claim_the_removed_reason(self):
		frappe.set_user(self.learner)
		result = submit_quiz(
			self.quiz,
			json.dumps([{"question_name": self.question.name, "answer": ["4"]}]),
			submission_reason="removed_by_admin",
		)
		frappe.set_user("Administrator")
		self.assertEqual(
			frappe.db.get_value("LMS Quiz Submission", result["submission"], "submission_reason"), "manual"
		)

	def test_a_removal_counts_as_an_attempt(self):
		self.remove(self.instructor)
		self.remove(self.instructor)
		frappe.set_user(self.learner)
		with self.assertRaises(MaximumAttemptsExceededError):
			submit_quiz(self.quiz, json.dumps([{"question_name": self.question.name, "answer": ["4"]}]))
