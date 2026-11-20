import frappe

from lms.lms.dashboard.batch import recalculate_batch_grades, set_student_grades
from lms.lms.test_helpers import BaseTestUtils


class TestGradebook(BaseTestUtils):
	def setUp(self):
		super().setUp()
		self._create_user(
			"frappe@example.com", "Frappe", "Admin", ["Moderator", "Course Creator", "Batch Evaluator"]
		)
		self._create_evaluator()
		self.learner = self._create_user("gb-learner@example.com", "Grade", "Learner", ["LMS Student"])
		course = self._create_course(title="Gradebook Course")
		self.questions = self._create_quiz_questions()
		self.quiz = self._create_quiz(self.questions, title="Gradebook Quiz")
		self.batch = self._create_batch(course.name, title="Gradebook Batch")
		self.batch.append("assessment", {"assessment_type": "LMS Quiz", "assessment_name": self.quiz.name})
		self.batch.save()
		self.enrollment = self._create_batch_enrollment(self.learner.name, self.batch.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def grade(self, **scores):
		return set_student_grades(self.batch.name, self.enrollment.name, scores)

	def weigh(self, exam, attendance, progress):
		self.batch.reload()
		self.batch.update(
			{
				"grading_method": "Weighted",
				"exam_weight": exam,
				"attendance_weight": attendance,
				"progress_weight": progress,
			}
		)
		self.batch.save()

	def test_exam_only_is_the_exam_score_plus_bonus(self):
		self.assertEqual(self.grade(exam_score=70, attendance_score=10, bonus_score=5)["final_score"], 75)

	def test_weighted_mixes_the_three_scores(self):
		self.weigh(60, 20, 20)
		grades = self.grade(exam_score=80, attendance_score=50, progress_score=100, bonus_score=2)
		self.assertEqual(grades["final_score"], 80 * 0.6 + 50 * 0.2 + 100 * 0.2 + 2)

	def test_weights_must_add_up_to_100(self):
		with self.assertRaises(frappe.ValidationError):
			self.weigh(60, 20, 10)

	def test_changing_the_weights_restates_final_scores(self):
		self.grade(exam_score=80, attendance_score=40)
		self.weigh(50, 50, 0)
		self.assertEqual(frappe.db.get_value("LMS Batch Enrollment", self.enrollment.name, "final_score"), 60)

	def test_a_score_above_100_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.grade(exam_score=120)

	def test_only_grade_fields_can_be_set(self):
		with self.assertRaises(frappe.ValidationError):
			set_student_grades(self.batch.name, self.enrollment.name, {"member": "someone@example.com"})

	def test_a_learner_cannot_grade(self):
		frappe.set_user(self.learner.name)
		with self.assertRaises(frappe.PermissionError):
			self.grade(bonus_score=50)

	def test_recalculate_fills_the_exam_score_from_the_best_attempt(self):
		for marks in (2, 4):
			frappe.get_doc(
				{
					"doctype": "LMS Quiz Submission",
					"quiz": self.quiz.name,
					"member": self.learner.name,
					"score_out_of": 5,
					"passing_percentage": 70,
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
		self.grade(bonus_score=3)

		self.assertEqual(recalculate_batch_grades(self.batch.name), 1)
		grades = frappe.db.get_value(
			"LMS Batch Enrollment",
			self.enrollment.name,
			["exam_score", "attendance_score", "bonus_score", "final_score"],
			as_dict=True,
		)
		best = max(frappe.get_all("LMS Quiz Submission", {"quiz": self.quiz.name}, pluck="percentage"))
		self.assertGreater(best, 0)
		self.assertEqual((grades.exam_score, grades.attendance_score, grades.bonus_score), (best, 0, 3))
		self.assertEqual(grades.final_score, best + 3)

	def test_a_learner_enrolling_themselves_cannot_set_their_own_score(self):
		other = self._create_user("gb-self@example.com", "Self", "Enroller", ["LMS Student"])
		frappe.db.set_value("LMS Batch", self.batch.name, "allow_self_enrollment", 1)
		frappe.set_user(other.name)
		enrollment = frappe.get_doc(
			{
				"doctype": "LMS Batch Enrollment",
				"batch": self.batch.name,
				"member": other.name,
				"bonus_score": 50,
			}
		).insert()
		self.assertEqual(
			frappe.db.get_value("LMS Batch Enrollment", enrollment.name, ["bonus_score", "final_score"]),
			(0, 0),
		)
