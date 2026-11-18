import json

import frappe

from lms.lms.doctype.lms_quiz.lms_quiz import (
	_attempt_seed,
	attempt_question_names,
	check_answer,
	submit_quiz,
)
from lms.lms.test_helpers import BaseTestUtils
from lms.lms.utils import get_quiz_with_questions


class TestQuizAttemptDraw(BaseTestUtils):
	"""A shuffled or limited quiz is drawn on the server. The page used to receive every
	question and draw for itself, so a learner could read and answer the questions their
	attempt left out."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		hash = frappe.generate_hash(length=6)
		cls.instructor = cls._create_user(f"qdi-{hash}@example.com", "Ida", "Instr", ["Course Creator"])
		cls.learner = cls._create_user(f"qdl-{hash}@example.com", "Lee", "Learner", ["LMS Student"])

		cls.questions = []
		for index in range(6):
			question = frappe.new_doc("LMS Question")
			question.update(
				{
					"question": f"Draw question {index} {hash}?",
					"type": "Choices",
					"option_1": "Right",
					"is_correct_1": 1,
					"option_2": "Wrong",
				}
			)
			question.save()
			cls.questions.append(question.name)

		quiz = frappe.new_doc("LMS Quiz")
		quiz.update(
			{
				"title": f"Draw Quiz {hash}",
				"passing_percentage": 50,
				"shuffle_questions": 1,
				"limit_questions_to": 2,
				"show_answers": 1,
			}
		)
		for name in cls.questions:
			quiz.append("questions", {"question": name, "marks": 1})
		quiz.save()
		cls.quiz = quiz.name

		course = cls._create_course(title=f"Draw Course {hash}", instructor=cls.instructor.email)
		chapter = cls._create_chapter(f"Draw Chapter {hash}", course.name)
		content = json.dumps(
			{"blocks": [{"id": "q1", "type": "quiz", "data": {"quiz": cls.quiz}}], "version": "2.29.0"}
		)
		cls._create_lesson(f"Draw Lesson {hash}", chapter.name, course.name, content)
		cls._create_enrollment(cls.learner.email, course.name)

	def setUp(self):
		super().setUp()
		frappe.session.user = self.learner.email

	def tearDown(self):
		frappe.session.user = "Administrator"
		super().tearDown()

	def _drawn(self):
		return attempt_question_names(self.quiz, self.learner.email)

	def _left_out(self):
		return next(name for name in self.questions if name not in self._drawn())

	def _submit(self, names, **kwargs):
		results = [{"question_name": name, "answer": ["Right"]} for name in names]
		return submit_quiz(self.quiz, json.dumps(results), **kwargs)

	def test_only_the_drawn_questions_reach_the_page(self):
		payload = get_quiz_with_questions(self.quiz)

		sent = [row["question"] for row in payload["quiz"]["questions"]]
		self.assertEqual(sent, self._drawn())
		self.assertEqual(len(sent), 2)
		self.assertEqual(set(payload["questions_by_name"]), set(sent))

	def test_a_reload_keeps_the_draw_and_a_submission_renews_it(self):
		first = get_quiz_with_questions(self.quiz)["quiz"]["questions"]
		self.assertEqual(get_quiz_with_questions(self.quiz)["quiz"]["questions"], first)

		seed_before = _attempt_seed(self.quiz, self.learner.email)
		self._submit(self._drawn())
		self.assertNotEqual(_attempt_seed(self.quiz, self.learner.email), seed_before)

	def test_an_answer_to_a_question_outside_the_draw_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self._submit([self._left_out()])

	def test_the_drawn_questions_submit(self):
		self.assertEqual(self._submit(self._drawn())["score"], 2)

	def test_live_checking_refuses_a_question_outside_the_draw(self):
		with self.assertRaises(frappe.ValidationError):
			check_answer(self.quiz, self._left_out(), "Choices", json.dumps(["Right"]))
		self.assertIn(1, check_answer(self.quiz, self._drawn()[0], "Choices", json.dumps(["Right"])))

	def test_shuffled_options_come_with_a_stable_order(self):
		frappe.db.set_value("LMS Quiz", self.quiz, "shuffle_options", 1)

		first = get_quiz_with_questions(self.quiz)["questions_by_name"]
		again = get_quiz_with_questions(self.quiz)["questions_by_name"]
		for name, row in first.items():
			self.assertEqual(sorted(row["option_order"]), list(range(1, 11)))
			self.assertEqual(again[name]["option_order"], row["option_order"])

	def test_options_keep_their_order_unless_shuffled(self):
		for row in get_quiz_with_questions(self.quiz)["questions_by_name"].values():
			self.assertNotIn("option_order", row)

	def test_only_the_latest_window_of_a_single_session_quiz_submits(self):
		frappe.db.set_value("LMS Quiz", self.quiz, "single_session", 1)
		earlier = get_quiz_with_questions(self.quiz)["quiz"]["attempt_token"]
		later = get_quiz_with_questions(self.quiz)["quiz"]["attempt_token"]
		self.assertNotEqual(earlier, later)

		for token in (earlier, None):
			with self.subTest(token=token), self.assertRaises(frappe.ValidationError):
				self._submit(self._drawn(), attempt_token=token)
		self.assertEqual(self._submit(self._drawn(), attempt_token=later)["score"], 2)

	def test_a_quiz_without_single_session_sends_no_token(self):
		self.assertNotIn("attempt_token", get_quiz_with_questions(self.quiz)["quiz"])
