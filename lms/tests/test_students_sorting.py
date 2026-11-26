import frappe

from lms.lms.dashboard.course import get_course_students
from lms.lms.test_helpers import BaseTestUtils


class TestStudentsSorting(BaseTestUtils):
	"""The course dashboard's students can be ordered by progress, lesson views or how many
	courses each is enrolled in; newest enrollment first stays the default."""

	def setUp(self):
		super().setUp()
		h = frappe.generate_hash(length=6)
		instructor = self._create_user(f"ss-i-{h}@example.com", "Ina", "Instr", ["Course Creator"]).name
		self.course = self._create_course(f"Sorting Course {h}", instructor=instructor).name
		other = self._create_course(f"Sorting Other {h}", instructor=instructor).name
		chapter = self._create_chapter(f"Chapter {h}", self.course).name
		self._create_chapter_reference(self.course, chapter)
		self.lessons = []
		for number in (1, 2):
			lesson = self._create_lesson(f"Lesson {number} {h}", chapter, self.course).name
			self._create_lesson_reference(chapter, lesson)
			self.lessons.append(lesson)

		# reader: most views, no progress. finisher: both lessons. joiner: in two courses.
		self.reader, self.finisher, self.joiner = (
			self._create_user(f"ss-{name}-{h}@example.com", name.title(), "Student", ["LMS Student"]).name
			for name in ("reader", "finisher", "joiner")
		)
		for member in (self.reader, self.finisher, self.joiner):
			self._create_enrollment(member, self.course)
		self._create_enrollment(self.joiner, other)
		for lesson in self.lessons:
			self._create_progress(self.finisher, self.course, lesson)
		frappe.get_doc(
			{
				"doctype": "LMS Lesson View",
				"member": self.reader,
				"course": self.course,
				"lesson": self.lessons[0],
				"date": "2026-11-20",
				"count": 7,
			}
		).insert(ignore_permissions=True)

	def first(self, sort_by=None):
		return get_course_students(self.course, sort_by=sort_by)["rows"][0]

	def test_each_order_puts_its_leader_first(self):
		self.assertEqual(self.first("progress")["member"], self.finisher)
		self.assertEqual((self.first("views")["member"], self.first("views")["views"]), (self.reader, 7))
		self.assertEqual(
			(self.first("enrollments")["member"], self.first("enrollments")["courses_enrolled"]),
			(self.joiner, 2),
		)

	def test_the_default_is_still_newest_enrollment_first(self):
		self.assertEqual(self.first()["member"], self.joiner)

	def test_an_unknown_order_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			get_course_students(self.course, sort_by="name; drop table")
