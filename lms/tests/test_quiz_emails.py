from unittest.mock import patch

import frappe
from frappe.utils import add_days, nowdate

from lms.lms.doctype.lms_quiz import lms_quiz
from lms.lms.test_helpers import BaseTestUtils


class TestQuizEmails(BaseTestUtils):
	def setUp(self):
		super().setUp()
		self._create_user(
			"frappe@example.com", "Frappe", "Admin", ["Moderator", "Course Creator", "Batch Evaluator"]
		)
		self._create_evaluator()
		self.course = self._create_course(title="Quiz Email Course")
		self.questions = self._create_quiz_questions()
		self.quiz = self._create_quiz(self.questions, title="Quiz Email Quiz")
		self._place_in_lesson(self.course.name, "LMS Quiz", self.quiz.name)

		self.enrolled = self._create_user("qe-enrolled@example.com", "Enrolled", "Learner", ["LMS Student"])
		self.expired = self._create_user("qe-expired@example.com", "Expired", "Learner", ["LMS Student"])
		self.batch_member = self._create_user("qe-batch@example.com", "Batch", "Learner", ["LMS Student"])
		self.outsider = self._create_user("qe-outsider@example.com", "Out", "Sider", ["LMS Student"])
		self._create_enrollment(self.enrolled.name, self.course.name)
		expired = self._create_enrollment(self.expired.name, self.course.name)
		frappe.db.set_value("LMS Enrollment", expired.name, "valid_until", add_days(nowdate(), -1))

		other_course = self._create_course(title="Quiz Email Batch Course")
		batch = self._create_batch(other_course.name, title="Quiz Email Batch")
		batch.append("assessment", {"assessment_type": "LMS Quiz", "assessment_name": self.quiz.name})
		batch.save()
		self._create_batch_enrollment(self.batch_member.name, batch.name)

	def schedule(self, start):
		self.quiz.reload()
		self.quiz.enable_scheduling = 1
		self.quiz.schedule_start = start
		self.quiz.save()

	def reminded(self):
		with patch.object(lms_quiz, "send_quiz_email") as send:
			lms_quiz.send_quiz_reminders()
		return {call.args[0] for call in send.call_args_list}

	def test_a_quiz_opening_tomorrow_reminds_its_course_and_batch_learners(self):
		self.schedule(f"{add_days(nowdate(), 1)} 10:00:00")
		self.assertEqual(self.reminded(), {self.enrolled.name, self.batch_member.name})

	def test_a_quiz_opening_later_reminds_no_one(self):
		self.schedule(f"{add_days(nowdate(), 2)} 10:00:00")
		self.assertEqual(self.reminded(), set())

	def test_grading_a_submission_emails_its_member(self):
		submission = frappe.get_doc(
			{
				"doctype": "LMS Quiz Submission",
				"quiz": self.quiz.name,
				"member": self.enrolled.name,
				"score_out_of": 15,
				"passing_percentage": 70,
				"result": [
					{"question_name": q.name, "question": q.question, "marks": 0, "marks_out_of": 5}
					for q in self.questions
				],
			}
		)
		with patch.object(lms_quiz, "send_quiz_email") as send:
			submission.insert(ignore_permissions=True)
			send.assert_not_called()

			submission.result[0].marks = 5
			submission.save(ignore_permissions=True)
		send.assert_called_once()
		self.assertEqual(send.call_args.args[:2], (self.enrolled.name, "quiz_result_template"))
		self.assertEqual(send.call_args.args[4]["score"], 5)

	def test_an_email_template_in_settings_replaces_the_wording(self):
		template = frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": "Quiz Reminder Test",
				"subject": "Tomorrow: {{ title }}",
				"response": "Hello {{ student_name }}",
			}
		).insert(ignore_permissions=True)
		frappe.db.set_single_value("LMS Settings", "quiz_reminder_template", template.name)
		with patch.object(frappe, "sendmail") as sendmail:
			lms_quiz.send_quiz_email(
				self.enrolled.name, "quiz_reminder_template", "default", "quiz_reminder", {"title": "Q1"}
			)
		kwargs = sendmail.call_args.kwargs
		self.assertEqual(kwargs["subject"], "Tomorrow: Q1")
		self.assertIn("Hello Enrolled Learner", kwargs["content"])
		self.assertIsNone(kwargs["template"])

	def test_a_failing_email_is_logged_not_raised(self):
		with patch.object(frappe, "sendmail", side_effect=frappe.OutgoingEmailError("no account")):
			lms_quiz.send_quiz_email(
				self.enrolled.name, "quiz_result_template", "graded", "quiz_result", {"title": "Q1"}
			)
		error = frappe.get_last_doc(
			"Error Log", {"reference_doctype": "User", "reference_name": self.enrolled.name}
		)
		self.assertIn("no account", error.error)
