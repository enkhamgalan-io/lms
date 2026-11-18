import json

import frappe

from lms.lms.doctype.course_lesson.course_lesson import get_quiz_progress
from lms.lms.doctype.lms_quiz.lms_quiz import check_answer, get_quiz_summary, submit_quiz
from lms.lms.test_helpers import BaseTestUtils


class TestQuizModes(BaseTestUtils):
	"""A survey or poll collects opinions: it is not scored, taking it completes its lesson,
	a poll shows everyone's answers, and an anonymous one hides who answered from staff."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		hash = frappe.generate_hash(length=6)
		cls.instructor = cls._create_user(f"qm-i-{hash}@example.com", "Ina", "Instr", ["Course Creator"]).name
		cls.learner = cls._create_user(f"qm-l-{hash}@example.com", "Lee", "Learner", ["LMS Student"]).name
		cls.opinion = cls._question(f"Which do you prefer {hash}?", no_correct_answer=1).name

		course = cls._create_course(f"Modes Course {hash}", instructor=cls.instructor)
		cls.course = course.name
		cls._create_enrollment(cls.learner, cls.course)
		cls.survey = cls._quiz(f"Survey {hash}", "Survey", is_anonymous=1)
		cls.poll = cls._quiz(f"Poll {hash}", "Poll")
		cls.survey_lesson = cls._place_in_lesson(cls.course, "LMS Quiz", cls.survey).name
		cls.poll_lesson = cls._place_in_lesson(cls.course, "LMS Quiz", cls.poll).name

	@classmethod
	def _question(cls, text, **values):
		return frappe.get_doc(
			{
				"doctype": "LMS Question",
				"question": text,
				"type": "Choices",
				"option_1": "Tea",
				"option_2": "Coffee",
				**values,
			}
		).insert()

	@classmethod
	def _quiz(cls, title, quiz_type, **values):
		quiz = frappe.get_doc({"doctype": "LMS Quiz", "title": title, "quiz_type": quiz_type, **values})
		quiz.append("questions", {"question": cls.opinion, "marks": 1})
		return quiz.insert().name

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def _answer(self, quiz, choice="Tea"):
		frappe.set_user(self.learner)
		result = submit_quiz(quiz, json.dumps([{"question_name": self.opinion, "answer": [choice]}]))
		frappe.set_user("Administrator")
		return result

	def test_an_opinion_question_needs_no_right_answer(self):
		with self.assertRaises(frappe.ValidationError):
			self._question(f"Graded {frappe.generate_hash(length=6)}?")

	def test_a_scored_quiz_refuses_an_opinion_question(self):
		with self.assertRaises(frappe.ValidationError):
			self._quiz(f"Scored {frappe.generate_hash(length=6)}", "Quiz")

	def test_a_survey_is_not_scored_and_has_nothing_to_check(self):
		result = self._answer(self.survey)
		self.assertEqual(result["quiz_type"], "Survey")
		self.assertNotIn("score", result)
		self.assertIsNone(result["summary"])

		frappe.set_user(self.learner)
		with self.assertRaises(frappe.ValidationError):
			check_answer(self.survey, self.opinion, "Choices", json.dumps(["Tea"]))

	def test_taking_a_survey_completes_its_lesson_even_where_passing_is_required(self):
		self.assertFalse(get_quiz_progress(self.survey_lesson, self.learner, "Passed", "Passed"))
		self._answer(self.survey)
		self.assertTrue(get_quiz_progress(self.survey_lesson, self.learner, "Passed", "Passed"))

	def test_a_poll_shows_everyones_answers_once_taken(self):
		frappe.set_user(self.learner)
		with self.assertRaises(frappe.PermissionError):
			get_quiz_summary(self.poll)

		summary = self._answer(self.poll, "Coffee")["summary"]
		self.assertEqual(summary[0]["answers"], [{"answer": "Coffee", "count": 1}])

	def test_an_anonymous_survey_hides_who_answered_from_staff(self):
		survey_submission = self._answer(self.survey)["submission"]
		poll_submission = self._answer(self.poll)["submission"]

		frappe.set_user(self.instructor)
		# The course's staff read a named poll's answers, so it is the anonymity that hides these.
		self.assertTrue(frappe.has_permission("LMS Quiz Submission", doc=poll_submission))
		self.assertFalse(frappe.has_permission("LMS Quiz Submission", doc=survey_submission))
		listed = frappe.get_list("LMS Quiz Submission", {"quiz": self.survey}, pluck="name")
		self.assertNotIn(survey_submission, listed)
		self.assertEqual(get_quiz_summary(self.survey)[0]["answers"][0]["count"], 1)

		frappe.set_user(self.learner)
		self.assertTrue(frappe.has_permission("LMS Quiz Submission", doc=survey_submission))
