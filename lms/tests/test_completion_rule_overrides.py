from unittest.mock import patch

import frappe

from lms.lms.doctype.course_lesson.course_lesson import get_completion_rules, save_progress
from lms.lms.test_helpers import BaseTestUtils

SITE = {
	"quiz": "Passed",
	"open_ended_quiz": "Passed",
	"assignment": "Attempted",
	"programming_exercise": None,
}


@patch("lms.lms.doctype.course_lesson.course_lesson._site_completion_rules", lambda: dict(SITE))
class TestCompletionRuleOverrides(BaseTestUtils):
	"""A course sets what its lessons require over the site's rules, and a batch over the
	course's for the learners who take it through that batch."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		hash = frappe.generate_hash(length=6)
		cls.instructor = cls._create_user(
			f"cro-i-{hash}@example.com", "Ina", "Instr", ["Course Creator"]
		).name
		cls.solo = cls._create_user(f"cro-s-{hash}@example.com", "Sol", "Learner", ["LMS Student"]).name
		cls.cohort = cls._create_user(f"cro-b-{hash}@example.com", "Coh", "Learner", ["LMS Student"]).name

		course = cls._create_course(f"Override Course {hash}", instructor=cls.instructor)
		course.quiz_completion = "Not required"
		course.assignment_completion = "Attempted"
		course.save()
		cls.course = course.name
		cls._create_enrollment(cls.solo, cls.course)

		cls._create_evaluator(cls.instructor)
		batch = cls._create_batch(
			cls.course, instructor=cls.instructor, title=f"Override Batch {hash}", evaluator=cls.instructor
		)
		batch.assignment_completion = "Passed"
		batch.save()
		cls._create_batch_enrollment(cls.cohort, batch.name)

		quiz = cls._create_quiz(cls._create_quiz_questions()[:1], title=f"Override Quiz {hash}")
		cls.quiz_lesson = cls._place_in_lesson(cls.course, "LMS Quiz", quiz.name).name

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_the_site_rules_stand_without_a_course(self):
		self.assertEqual(get_completion_rules(), SITE)

	def test_a_course_sets_its_own_and_leaves_the_rest_to_the_site(self):
		rules = get_completion_rules(self.course, self.solo)
		self.assertIsNone(rules["quiz"])
		self.assertIsNone(rules["open_ended_quiz"])
		self.assertEqual(rules["assignment"], "Attempted")
		self.assertIsNone(rules["programming_exercise"])

	def test_a_batch_sets_its_own_for_its_learners_only(self):
		self.assertEqual(get_completion_rules(self.course, self.cohort)["assignment"], "Passed")
		self.assertEqual(get_completion_rules(self.course, self.solo)["assignment"], "Attempted")
		# The batch leaves quizzes to the course.
		self.assertIsNone(get_completion_rules(self.course, self.cohort)["quiz"])

	def test_a_quiz_lesson_completes_unattempted_when_the_course_waives_quizzes(self):
		frappe.set_user(self.solo)
		save_progress(self.quiz_lesson, self.course)
		self.assertEqual(
			frappe.db.get_value(
				"LMS Course Progress", {"lesson": self.quiz_lesson, "member": self.solo}, "status"
			),
			"Complete",
		)
