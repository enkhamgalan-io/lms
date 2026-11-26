import io
import json
from unittest.mock import patch

import frappe
from openpyxl import load_workbook

from lms.lms.doctype.lms_quiz.lms_quiz import download_quiz_summary, submit_quiz
from lms.lms.test_helpers import BaseTestUtils


class TestSurveyResults(BaseTestUtils):
	"""A survey's staff download its tally as xlsx, and each answer pings an open results page."""

	def setUp(self):
		super().setUp()
		h = frappe.generate_hash(length=6)
		self.instructor = self._create_user(f"sr-i-{h}@example.com", "Ina", "Instr", ["Course Creator"]).name
		self.learners = [
			self._create_user(f"sr-l{i}-{h}@example.com", "Lee", f"Learner{i}", ["LMS Student"]).name
			for i in range(3)
		]
		self.question = frappe.get_doc(
			{
				"doctype": "LMS Question",
				"question": f"Which do you prefer {h}?",
				"type": "Choices",
				"option_1": "Tea",
				"option_2": "Coffee",
				"no_correct_answer": 1,
			}
		).insert()
		course = self._create_course(f"Results Course {h}", instructor=self.instructor).name
		survey = frappe.get_doc(
			{"doctype": "LMS Quiz", "title": f"Results Survey {h}", "quiz_type": "Survey", "is_anonymous": 1}
		)
		survey.append("questions", {"question": self.question.name, "marks": 1})
		self.survey = survey.insert().name
		self._place_in_lesson(course, "LMS Quiz", self.survey)
		for learner in self.learners:
			self._create_enrollment(learner, course)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def answer(self, learner, choice):
		frappe.set_user(learner)
		try:
			with patch.object(frappe, "publish_realtime") as publish:
				submit_quiz(
					self.survey, json.dumps([{"question_name": self.question.name, "answer": [choice]}])
				)
			return publish
		finally:
			frappe.set_user("Administrator")

	def download(self, user):
		frappe.set_user(user)
		try:
			download_quiz_summary(self.survey)
			sheet = load_workbook(io.BytesIO(frappe.response["filecontent"])).active
			return [list(row) for row in sheet.iter_rows(values_only=True)]
		finally:
			frappe.set_user("Administrator")

	def test_staff_download_the_tally(self):
		for learner, choice in zip(self.learners, ("Tea", "Tea", "Coffee"), strict=True):
			self.answer(learner, choice)
		rows = self.download(self.instructor)
		self.assertEqual(rows[0], ["Question", "Answer", "Count", "Share of responses (%)"])
		self.assertEqual([row[1:] for row in rows[1:]], [["Tea", 2, 66.7], ["Coffee", 1, 33.3]])

	def test_a_learner_cannot_download_it(self):
		with self.assertRaises(frappe.PermissionError):
			self.download(self.learners[0])

	def test_an_answer_pings_the_quiz_room_with_its_name_only(self):
		publish = self.answer(self.learners[0], "Tea")
		publish.assert_any_call(
			"quiz_summary_updated",
			{"quiz": self.survey},
			doctype="LMS Quiz",
			docname=self.survey,
			after_commit=True,
		)
