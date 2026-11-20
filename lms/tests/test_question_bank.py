import frappe

from lms.lms.doctype.lms_quiz.lms_quiz import attempt_question_names
from lms.lms.test_helpers import BaseTestUtils


class TestQuestionBank(BaseTestUtils):
	def setUp(self):
		super().setUp()
		self._create_user(
			"frappe@example.com", "Frappe", "Admin", ["Moderator", "Course Creator", "Batch Evaluator"]
		)
		self.learner = self._create_user("qb-learner@example.com", "Bank", "Learner", ["LMS Student"])
		self.bank = {}
		questions = []
		for bank, difficulty, count in (
			("Labour Law", "Easy", 3),
			("Labour Law", "Hard", 1),
			("Tax Law", "", 2),
		):
			for n in range(count):
				question = frappe.get_doc(
					{
						"doctype": "LMS Question",
						"question": f"{bank} {difficulty} {n}?",
						"type": "Choices",
						"option_1": "Yes",
						"is_correct_1": 1,
						"option_2": "No",
						"question_bank": bank,
						"difficulty": difficulty,
					}
				).insert()
				self.bank[question.name] = (bank, difficulty)
				questions.append(question)
		self.quiz = self._create_quiz(questions, title="Bank Quiz")

	def set_rules(self, *rules):
		self.quiz.reload()
		self.quiz.set(
			"random_rules",
			[
				{"question_bank": bank, "difficulty": difficulty, "count": count}
				for bank, difficulty, count in rules
			],
		)
		self.quiz.save()

	def test_rules_shuffle_and_limit_the_quiz_to_their_total(self):
		self.set_rules(("Labour Law", "Easy", 2), ("Tax Law", "", 1))
		self.assertEqual((self.quiz.shuffle_questions, self.quiz.limit_questions_to), (1, 3))
		self.assertEqual(self.quiz.total_marks, 15)

	def test_an_attempt_draws_each_rules_count_from_its_bank(self):
		# Typed differently from the questions' bank on purpose: case and spaces do not count.
		self.set_rules(("labour law ", "Easy", 2), ("Tax Law", "", 1))
		drawn = attempt_question_names(self.quiz.name, self.learner.name)
		self.assertEqual(
			sorted(self.bank[name] for name in drawn), [("Labour Law", "Easy")] * 2 + [("Tax Law", "")]
		)
		self.assertEqual(drawn, attempt_question_names(self.quiz.name, self.learner.name))

	def test_a_rule_asking_for_more_than_the_quiz_has_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.set_rules(("Labour Law", "Hard", 2))

	def test_rules_covering_every_question_draw_them_all(self):
		self.set_rules(("Labour Law", "", 4), ("Tax Law", "", 2))
		self.assertEqual(self.quiz.limit_questions_to, 0)
		self.assertEqual(set(attempt_question_names(self.quiz.name, self.learner.name)), set(self.bank))
