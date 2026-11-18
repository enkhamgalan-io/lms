import frappe

from lms.lms.api import get_popular_courses
from lms.lms.doctype.lms_batch.lms_batch import has_permission as batch_has_permission
from lms.lms.permissions import can_access_course, course_query_conditions, hidden_by_organization
from lms.lms.test_helpers import BaseTestUtils
from lms.lms.utils import get_batches, get_courses


class TestOrganizationVisibility(BaseTestUtils):
	"""A course or batch shown to some organizations reaches their people and the people of
	the organizations under them. Everyone else neither lists, opens nor joins it."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		hash = frappe.generate_hash(length=6)
		ministry = cls._organization(f"Vis Ministry {hash}", is_group=1)
		cls.agency = cls._organization(f"Vis Agency {hash}", parent=ministry, is_group=1)
		department = cls._organization(f"Vis Department {hash}", parent=cls.agency)
		other = cls._organization(f"Vis Other {hash}", parent=ministry)

		cls.instructor = cls._create_user(f"ov-i-{hash}@example.com", "Ina", "Instr", ["Course Creator"])
		cls.inside = cls._learner(f"ov-in-{hash}@example.com", department)
		cls.outside = cls._learner(f"ov-out-{hash}@example.com", other)
		cls.moderator = cls._create_user(f"ov-m-{hash}@example.com", "Mo", "Derator", ["Moderator"]).name

		cls.limited = cls._create_course(f"Vis Limited {hash}", instructor=cls.instructor.name).name
		cls.open = cls._create_course(f"Vis Open {hash}", instructor=cls.instructor.name).name
		course = frappe.get_doc("LMS Course", cls.limited)
		course.append("organizations", {"organization": cls.agency})
		course.save()

		cls._create_evaluator(cls.instructor.name)
		batch = cls._create_batch(
			cls.open, instructor=cls.instructor.name, title=f"Vis Batch {hash}", evaluator=cls.instructor.name
		)
		batch.allow_self_enrollment = 1
		batch.append("organizations", {"organization": cls.agency})
		batch.save()
		cls.batch = batch.name

	@classmethod
	def _organization(cls, name, parent=None, is_group=0):
		return (
			frappe.get_doc(
				{
					"doctype": "LMS Organization",
					"organization_name": name,
					"parent_lms_organization": parent,
					"is_group": is_group,
				}
			)
			.insert()
			.name
		)

	@classmethod
	def _learner(cls, email, organization):
		user = cls._create_user(email, "Lea", email.split("@")[0], ["LMS Student"])
		frappe.db.set_value("User", user.name, "organization", organization)
		return user.name

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def _courses(self, user):
		frappe.set_user(user)
		return {row.name for row in get_courses(limit_page_length=500)}

	def _enroll_self(self, doctype, field, name):
		return frappe.get_doc({"doctype": doctype, field: name, "member": frappe.session.user}).insert()

	def test_the_course_list_follows_the_organization(self):
		self.assertIn(self.limited, self._courses(self.inside))
		self.assertNotIn(self.limited, self._courses(self.outside))
		self.assertIn(self.open, self._courses(self.outside))
		self.assertIn(self.limited, self._courses(self.moderator))

	def test_the_home_page_leaves_it_out_too(self):
		frappe.set_user(self.outside)
		self.assertEqual(hidden_by_organization("LMS Course"), [self.limited])
		self.assertNotIn(self.limited, get_popular_courses())

	def _readable_courses(self, user):
		condition = course_query_conditions(user)
		return set(frappe.db.sql_list(f"select name from `tabLMS Course` where {condition or '1=1'}"))

	def test_a_learner_outside_cannot_open_it(self):
		self.assertFalse(can_access_course(self.limited, user=self.outside))
		self.assertNotIn(self.limited, self._readable_courses(self.outside))

		self.assertTrue(can_access_course(self.limited, user=self.inside))
		self.assertIn(self.limited, self._readable_courses(self.inside))

	def test_guests_and_unplaced_people_are_outside(self):
		self.assertIn(self.limited, hidden_by_organization("LMS Course", "Guest"))
		self.assertIn(self.limited, hidden_by_organization("LMS Course", self.instructor.name))

	def test_only_people_inside_enroll_themselves(self):
		frappe.set_user(self.outside)
		with self.assertRaises(frappe.PermissionError):
			self._enroll_self("LMS Enrollment", "course", self.limited)

		frappe.set_user(self.inside)
		self._enroll_self("LMS Enrollment", "course", self.limited)

	def test_someone_enrolled_by_staff_keeps_access(self):
		frappe.set_user(self.instructor.name)
		frappe.get_doc({"doctype": "LMS Enrollment", "course": self.limited, "member": self.outside}).insert()

		self.assertTrue(can_access_course(self.limited, user=self.outside))
		self.assertIn(self.limited, self._readable_courses(self.outside))

	def test_batches_follow_the_same_rule(self):
		frappe.set_user(self.outside)
		self.assertNotIn(self.batch, {row.name for row in get_batches(limit_page_length=500)})
		batch = frappe.get_doc("LMS Batch", self.batch)
		self.assertFalse(batch_has_permission(batch, "read", self.outside))
		self.assertTrue(batch_has_permission(batch, "read", self.inside))
		with self.assertRaises(frappe.PermissionError):
			self._enroll_self("LMS Batch Enrollment", "batch", self.batch)

		frappe.set_user(self.inside)
		self.assertIn(self.batch, {row.name for row in get_batches(limit_page_length=500)})
		self._enroll_self("LMS Batch Enrollment", "batch", self.batch)
