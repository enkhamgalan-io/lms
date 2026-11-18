import frappe

from lms.lms.api import (
	add_students_to_batch,
	enroll_students_in_course,
	get_member_enrollment_options,
	search_users_to_enroll,
)
from lms.lms.dashboard.course import set_course_access
from lms.lms.test_helpers import BaseTestUtils


class TestOrganizationEnrollment(BaseTestUtils):
	"""An Organization Manager enrolls the people they manage in courses and batches open
	to them, and no one else."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		hash = frappe.generate_hash(length=6)
		cls.agency = cls._organization(f"Enr Agency {hash}", is_group=1)
		department = cls._organization(f"Enr Department {hash}", parent=cls.agency)
		other = cls._organization(f"Enr Other {hash}")

		cls.instructor = cls._create_user(f"oe-i-{hash}@example.com", "Ina", "Instr", ["Course Creator"]).name
		cls.hr = cls._create_user(f"oe-hr-{hash}@example.com", "Hana", "Hr", ["LMS Student"]).name
		cls.inside = cls._learner(f"oe-in-{hash}@example.com", department)
		cls.outside = cls._learner(f"oe-out-{hash}@example.com", other)
		agency = frappe.get_doc("LMS Organization", cls.agency)
		agency.append("managers", {"user": cls.hr})
		agency.save()

		course = cls._create_course(f"Enr Assigned {hash}", instructor=cls.instructor)
		course.disable_self_learning = 1
		course.save()
		cls.course = course.name
		elsewhere = cls._create_course(f"Enr Elsewhere {hash}", instructor=cls.instructor)
		elsewhere.append("organizations", {"organization": other})
		elsewhere.save()
		cls.elsewhere = elsewhere.name

		cls._create_evaluator(cls.instructor)
		cls.batch = cls._create_batch(
			cls.course, instructor=cls.instructor, title=f"Enr Batch {hash}", evaluator=cls.instructor
		).name

	@classmethod
	def _organization(cls, name, parent=None, is_group=0):
		doc = frappe.get_doc(
			{
				"doctype": "LMS Organization",
				"organization_name": name,
				"parent_lms_organization": parent,
				"is_group": is_group,
			}
		)
		return doc.insert().name

	@classmethod
	def _learner(cls, email, organization):
		user = cls._create_user(email, "Lea", email.split("@")[0], ["LMS Student"])
		frappe.db.set_value("User", user.name, "organization", organization)
		return user.name

	def setUp(self):
		super().setUp()
		frappe.set_user(self.hr)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_they_enroll_their_own_people_in_a_course(self):
		result = enroll_students_in_course(self.course, [self.inside, self.outside])
		self.assertEqual(result["added"], [self.inside], result["errors"])
		self.assertEqual([error["member"] for error in result["errors"]], [self.outside])

	def test_not_in_a_course_shown_to_other_organizations(self):
		result = enroll_students_in_course(self.elsewhere, [self.inside])
		self.assertEqual(result["added"], [])
		self.assertEqual(len(result["errors"]), 1)

	def test_they_enroll_their_own_people_in_a_batch(self):
		result = add_students_to_batch(self.batch, [self.inside, self.outside])
		self.assertEqual(result["added"], [self.inside], result["errors"])
		self.assertEqual([error["member"] for error in result["errors"]], [self.outside])

	def test_the_people_picker_holds_only_their_people(self):
		found = {
			row["value"] for row in search_users_to_enroll("LMS Course", self.course, "oe-", page_length=50)
		}
		self.assertIn(self.inside, found)
		self.assertNotIn(self.outside, found)

	def test_the_options_follow_what_the_member_may_join(self):
		enroll_students_in_course(self.course, [self.inside])
		options = get_member_enrollment_options(self.inside)
		courses = {row.name: row.enrolled for row in options["courses"]}
		self.assertTrue(courses[self.course])
		self.assertNotIn(self.elsewhere, courses)
		self.assertIn(self.batch, {row.name for row in options["batches"]})

		with self.assertRaises(frappe.PermissionError):
			get_member_enrollment_options(self.outside)

	def test_they_extend_access_for_their_people_only(self):
		enroll_students_in_course(self.course, [self.inside])
		mine = frappe.db.get_value("LMS Enrollment", {"course": self.course, "member": self.inside})
		set_course_access(self.course, mine, "2099-12-31")
		self.assertEqual(str(frappe.db.get_value("LMS Enrollment", mine, "valid_until")), "2099-12-31")

		frappe.set_user(self.instructor)
		enroll_students_in_course(self.course, [self.outside])
		theirs = frappe.db.get_value("LMS Enrollment", {"course": self.course, "member": self.outside})
		frappe.set_user(self.hr)
		with self.assertRaises(frappe.PermissionError):
			set_course_access(self.course, theirs, "2099-12-31")
