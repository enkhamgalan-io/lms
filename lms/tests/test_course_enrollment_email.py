from unittest.mock import patch

import frappe

from lms.lms.test_helpers import BaseTestUtils


class TestCourseEnrollmentEmail(BaseTestUtils):
	"""A learner whom someone else enrolls in a course is told by email; one who enrolls
	themselves is not, and a failed email never undoes the enrollment."""

	def setUp(self):
		super().setUp()
		h = frappe.generate_hash(length=6)
		self.moderator = self._create_user(f"ce-mod-{h}@example.com", "Mo", "Derator", ["Moderator"]).name
		self.learner = self._create_user(f"ce-l-{h}@example.com", "Lee", "Learner", ["LMS Student"]).name
		instructor = self._create_user(f"ce-i-{h}@example.com", "Ina", "Instr", ["Course Creator"]).name
		self.course = self._create_course(f"Enrollment Mail Course {h}", instructor=instructor)
		self.mail = patch.dict(frappe.conf, {"mail_login": "lms@example.com"})
		self.mail.start()

	def tearDown(self):
		self.mail.stop()
		frappe.set_user("Administrator")
		frappe.db.set_single_value("LMS Settings", "course_enrollment_template", None)
		super().tearDown()

	def enroll(self, as_user, **sendmail):
		frappe.set_user(as_user)
		try:
			with patch.object(frappe, "sendmail", **sendmail) as sent:
				enrollment = frappe.get_doc(
					{"doctype": "LMS Enrollment", "member": self.learner, "course": self.course.name}
				).insert()
			return enrollment, sent
		finally:
			frappe.set_user("Administrator")

	def test_staff_enrolling_a_learner_emails_them(self):
		_, sent = self.enroll(self.moderator)
		sent.assert_called_once()
		kwargs = sent.call_args.kwargs
		self.assertEqual((kwargs["recipients"], kwargs["template"]), (self.learner, "course_enrollment"))
		self.assertEqual(kwargs["args"]["title"], self.course.title)

	def test_a_learner_enrolling_themselves_gets_no_email(self):
		_, sent = self.enroll(self.learner)
		sent.assert_not_called()

	def test_the_settings_template_replaces_the_wording(self):
		template = frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": f"Course Enrolled {frappe.generate_hash(length=6)}",
				"subject": "Welcome to {{ title }}",
				"response": "Hello {{ student_name }}",
			}
		).insert(ignore_permissions=True)
		frappe.db.set_single_value("LMS Settings", "course_enrollment_template", template.name)
		_, sent = self.enroll(self.moderator)
		kwargs = sent.call_args.kwargs
		self.assertEqual(kwargs["subject"], f"Welcome to {self.course.title}")
		self.assertIsNone(kwargs["template"])
		self.assertIn("Hello", kwargs["content"])

	def test_a_failed_email_keeps_the_enrollment(self):
		with patch.object(frappe, "log_error") as logged:
			enrollment, _ = self.enroll(self.moderator, side_effect=frappe.OutgoingEmailError("down"))
		self.assertTrue(frappe.db.exists("LMS Enrollment", enrollment.name))
		self.assertEqual(logged.call_args.kwargs["reference_name"], enrollment.name)
