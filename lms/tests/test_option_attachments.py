import base64

import frappe

from lms.lms.doctype.course_lesson import course_lesson
from lms.lms.doctype.lms_question.lms_question import serve_question_resource
from lms.lms.test_helpers import BaseTestUtils
from lms.lms.utils import QUESTION_PRIVATE_MEDIA_ENDPOINT, get_quiz_with_questions

ONE_PIXEL_PNG = base64.b64decode(
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M8AAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
)


class TestOptionAttachments(BaseTestUtils):
	"""An answer option can carry a file. Learners who may take the quiz get it through the
	access-gated question endpoint; anyone else is refused."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		h = frappe.generate_hash(length=6)
		cls.instructor = cls._create_user(f"oa-i-{h}@example.com", "Ina", "Instr", ["Course Creator"])
		cls.student = cls._create_user(f"oa-s-{h}@example.com", "Sam", "Student", ["LMS Student"])
		cls.outsider = cls._create_user(f"oa-o-{h}@example.com", "Otto", "Out", ["LMS Student"])

		frappe.set_user(cls.instructor.email)
		try:
			# An unattached private upload, as FileUploader leaves it before the question is saved.
			cls.file_url = (
				frappe.get_doc(
					{
						"doctype": "File",
						"file_name": f"option_{h}.png",
						"is_private": 1,
						"content": base64.b64encode(ONE_PIXEL_PNG + h.encode()).decode(),
						"decode": True,
					}
				)
				.insert(ignore_permissions=True)
				.file_url
			)
			cls.question = frappe.get_doc(
				{
					"doctype": "LMS Question",
					"question": f"Which shape {h}?",
					"type": "Choices",
					"option_1": "Square",
					"is_correct_1": 1,
					"option_1_attachment": cls.file_url,
					"option_2": "Circle",
				}
			).insert()
		finally:
			frappe.set_user("Administrator")

		cls.quiz = cls._create_quiz([cls.question], title=f"Option Files Quiz {h}")
		course = cls._create_course(title=f"Option Files Course {h}", instructor=cls.instructor.email)
		cls._place_in_lesson(course.name, "LMS Quiz", cls.quiz.name)
		cls._create_enrollment(cls.student.email, course.name)

	def _serve_as(self, user):
		served = object()
		original = course_lesson._serve_private_file
		course_lesson._serve_private_file = lambda relative_path, filename: served
		frappe.set_user(user)
		try:
			return serve_question_resource(self.file_url) is served
		finally:
			course_lesson._serve_private_file = original
			frappe.set_user("Administrator")

	def test_a_file_needs_text_beside_it(self):
		question = frappe.get_doc("LMS Question", self.question.name)
		question.option_2 = ""
		question.option_3 = "Triangle"
		question.option_2_attachment = self.file_url
		with self.assertRaises(frappe.ValidationError):
			question.save()

	def test_the_learner_receives_the_file_through_the_gated_endpoint(self):
		frappe.set_user(self.student.email)
		try:
			row = get_quiz_with_questions(self.quiz.name)["questions_by_name"][self.question.name]
		finally:
			frappe.set_user("Administrator")
		self.assertTrue(row["option_1_attachment"].startswith(QUESTION_PRIVATE_MEDIA_ENDPOINT))
		self.assertIsNone(row["option_2_attachment"])

	def test_an_enrolled_learner_is_served_the_file(self):
		self.assertTrue(self._serve_as(self.student.email))

	def test_an_outsider_is_refused_the_file(self):
		with self.assertRaises(frappe.PermissionError):
			self._serve_as(self.outsider.email)
