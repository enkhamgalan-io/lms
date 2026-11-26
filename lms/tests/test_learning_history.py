import frappe
from frappe.utils import getdate

from lms.lms.api import get_learning_history
from lms.lms.test_helpers import BaseTestUtils


class TestLearningHistory(BaseTestUtils):
	"""A member's history lists each course and batch with its dates, score, credit hours and
	certificate, for the member and the staff who manage them, and for no one else."""

	def setUp(self):
		super().setUp()
		h = frappe.generate_hash(length=6)
		instructor = self._create_user(f"lh-i-{h}@example.com", "Ina", "Instr", ["Course Creator"]).name
		self.member = self._create_user(f"lh-m-{h}@example.com", "Bat", "Member", ["LMS Student"])
		self.peer = self._create_user(f"lh-p-{h}@example.com", "Peer", "Learner", ["LMS Student"]).name
		self.moderator = self._create_user(f"lh-mod-{h}@example.com", "Mo", "Derator", ["Moderator"]).name

		self.course = self._create_course(f"History Course {h}", instructor=instructor).name
		enrollment = self._create_enrollment(self.member.name, self.course)
		frappe.db.set_value("LMS Enrollment", enrollment.name, "progress", 100)
		frappe.get_doc(
			{
				"doctype": "LMS Credit Entry",
				"member": self.member.name,
				"source_type": "LMS Course",
				"source": self.course,
				"hours": 4,
				"date": "2026-10-05",
			}
		).insert(ignore_permissions=True)
		quiz = self._create_quiz(self._create_quiz_questions(), title=f"History Quiz {h}").name
		# As a quiz placed in one of the course's lessons has it; submissions fetch it from here.
		frappe.db.set_value("LMS Quiz", quiz, "course", self.course)
		# Two attempts at one quiz: the history keeps the better one.
		for percentage in (40, 90):
			submission = frappe.get_doc(
				{
					"doctype": "LMS Quiz Submission",
					"quiz": quiz,
					"member": self.member.name,
					"passing_percentage": 50,
				}
			).insert(ignore_permissions=True)
			# The graded result, which the controller would compute from answered rows.
			frappe.db.set_value("LMS Quiz Submission", submission.name, "percentage", percentage)

		self._create_evaluator(instructor)
		self.batch = self._create_batch(
			self.course, instructor=instructor, title=f"History Batch {h}", evaluator=instructor
		).name
		batch_enrollment = self._create_batch_enrollment(self.member.name, self.batch)
		frappe.db.set_value("LMS Batch Enrollment", batch_enrollment.name, "final_score", 82)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def history(self, user):
		frappe.set_user(user)
		try:
			return {row["name"]: row for row in get_learning_history(self.member.username)}
		finally:
			frappe.set_user("Administrator")

	def test_a_finished_course_shows_its_date_best_quiz_score_and_credit(self):
		row = self.history(self.member.name)[self.course]
		self.assertEqual(
			(row["type"], row["progress"], row["score"], row["credit_hours"], row["completed_on"]),
			("course", 100, 90, 4, getdate("2026-10-05")),
		)

	def test_a_batch_shows_its_final_score(self):
		row = self.history(self.member.name)[self.batch]
		self.assertEqual((row["type"], row["score"], row["completed_on"]), ("batch", 82, None))

	def test_a_moderator_reads_it(self):
		self.assertIn(self.course, self.history(self.moderator))

	def test_another_learner_is_refused(self):
		with self.assertRaises(frappe.PermissionError):
			self.history(self.peer)
