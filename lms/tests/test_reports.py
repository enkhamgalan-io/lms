import frappe
from frappe.utils import add_days, getdate, nowdate

from lms.lms.doctype.lms_lesson_view.lms_lesson_view import record_view
from lms.lms.report.lesson_access_log import lesson_access_log
from lms.lms.report.login_log import login_log
from lms.lms.report.quiz_results_summary import quiz_results_summary
from lms.lms.test_helpers import BaseTestUtils

PERIOD = {"from_date": add_days(nowdate(), -1), "to_date": nowdate()}


class TestReports(BaseTestUtils):
	def setUp(self):
		super().setUp()
		self._create_user(
			"frappe@example.com", "Frappe", "Admin", ["Moderator", "Course Creator", "Batch Evaluator"]
		)
		self.first = self._create_user("rp-first@example.com", "First", "Learner", ["LMS Student"])
		self.second = self._create_user("rp-second@example.com", "Second", "Learner", ["LMS Student"])
		self.course = self._create_course(title="Report Course")
		chapter = self._create_chapter("Report Chapter", self.course.name)
		self.lesson = self._create_lesson("Report Lesson", chapter.name, self.course.name)
		self.questions = self._create_quiz_questions()

	def submit(self, quiz, member, marks):
		frappe.get_doc(
			{
				"doctype": "LMS Quiz Submission",
				"quiz": quiz.name,
				"member": member,
				"score_out_of": 5,
				"passing_percentage": 50,
				"result": [
					{
						"question_name": self.questions[0].name,
						"question": self.questions[0].question,
						"marks": marks,
						"marks_out_of": 5,
					}
				],
			}
		).insert(ignore_permissions=True)

	def test_quiz_results_summary_reports_the_spread_and_pass_rate(self):
		quiz = self._create_quiz(self.questions, title="Report Quiz")
		self._place_in_lesson(self.course.name, "LMS Quiz", quiz.name)
		self.submit(quiz, self.first.name, 5)
		self.submit(quiz, self.first.name, 1)
		self.submit(quiz, self.second.name, 3)
		survey = self._create_quiz(self.questions, title="Report Survey")
		frappe.db.set_value("LMS Quiz", survey.name, "quiz_type", "Survey")
		self.submit(survey, self.first.name, 0)

		print(
			"DBG",
			frappe.get_all("LMS Quiz Submission", {"quiz": quiz.name}, ["course", "creation", "percentage"]),
			frappe.db.get_value("LMS Quiz", quiz.name, "quiz_type"),
		)
		_columns, rows = quiz_results_summary.execute({**PERIOD, "course": self.course.name})
		self.assertEqual([row.quiz for row in rows], [quiz.name])
		row = rows[0]
		percentages = frappe.get_all("LMS Quiz Submission", {"quiz": quiz.name}, pluck="percentage")
		passed = sum(1 for p in percentages if p >= 50)
		self.assertEqual((row.attempts, row.learners), (3, 2))
		self.assertEqual((row.highest, row.lowest), (max(percentages), min(percentages)))
		self.assertEqual(row.average, round(sum(percentages) / 3, 1))
		self.assertEqual(row.pass_rate, round(100 * passed / 3, 1))

	def test_lesson_access_log_sums_views_and_counts_learners(self):
		record_view(self.first.name, self.course.name, self.lesson.name)
		record_view(self.first.name, self.course.name, self.lesson.name)
		record_view(self.second.name, self.course.name, self.lesson.name)

		_columns, rows = lesson_access_log.execute(
			{**PERIOD, "course": self.course.name, "group_by": "Month"}
		)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].period, getdate().strftime("%Y-%m"))
		self.assertEqual((rows[0].views, rows[0].learners), (3, 2))

		_columns, rows = lesson_access_log.execute({**PERIOD, "member": self.second.name})
		self.assertEqual((rows[0].views, rows[0].learners), (1, 1))

	def test_login_log_lists_logins_for_a_user(self):
		frappe.get_doc(
			{
				"doctype": "Activity Log",
				"operation": "Login",
				"status": "Success",
				"user": self.first.name,
				"subject": "logged in",
			}
		).insert(ignore_permissions=True)
		_columns, rows = login_log.execute({**PERIOD, "user": self.first.name})
		# Activity Log is virtual, so a savepoint does not undo earlier runs' rows.
		self.assertTrue(rows)
		self.assertEqual({(row.user, row.operation) for row in rows}, {(self.first.name, "Login")})

	def test_a_moderator_can_run_every_report(self):
		from frappe.desk.query_report import run

		frappe.set_user("frappe@example.com")
		try:
			for report in ("Login Log", "Lesson Access Log", "Quiz Results Summary"):
				self.assertIn("result", run(report, filters=PERIOD), report)
		finally:
			frappe.set_user("Administrator")

	def test_a_learner_cannot_run_them(self):
		from frappe.desk.query_report import run

		frappe.set_user(self.first.name)
		try:
			for report in ("Login Log", "Lesson Access Log", "Quiz Results Summary"):
				with self.assertRaises(frappe.PermissionError, msg=report):
					run(report, filters=PERIOD)
		finally:
			frappe.set_user("Administrator")
