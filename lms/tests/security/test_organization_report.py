import frappe

from lms.lms.api import get_organization_report
from lms.lms.test_helpers import BaseTestUtils


class TestOrganizationReport(BaseTestUtils):
	"""The organization report holds the enrollments of the people the caller manages,
	and no one else's."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		hash = frappe.generate_hash(length=6)
		cls.agency = cls._organization(f"Rep Agency {hash}", is_group=1)
		cls.department = cls._organization(f"Rep Department {hash}", parent=cls.agency)
		cls.other = cls._organization(f"Rep Other {hash}")

		instructor = cls._create_user(f"or-i-{hash}@example.com", "Ina", "Instr", ["Course Creator"]).name
		cls.hr = cls._create_user(f"or-hr-{hash}@example.com", "Hana", "Hr", ["LMS Student"]).name
		cls.in_agency = cls._learner(f"or-a-{hash}@example.com", cls.agency)
		cls.in_department = cls._learner(f"or-d-{hash}@example.com", cls.department)
		cls.outside = cls._learner(f"or-o-{hash}@example.com", cls.other)
		agency = frappe.get_doc("LMS Organization", cls.agency)
		agency.append("managers", {"user": cls.hr})
		agency.save()

		cls.course = cls._create_course(f"Rep Course {hash}", instructor=instructor).name
		cls.second = cls._create_course(f"Rep Second {hash}", instructor=instructor).name
		for member in (cls.in_agency, cls.in_department, cls.outside):
			cls._create_enrollment(member, cls.course)
		cls._create_enrollment(cls.in_department, cls.second)

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

	def _pairs(self, **filters):
		return {(row["member"], row["course"]) for row in get_organization_report(**filters)["rows"]}

	def test_it_holds_their_people_only(self):
		self.assertEqual(
			self._pairs(),
			{
				(self.in_agency, self.course),
				(self.in_department, self.course),
				(self.in_department, self.second),
			},
		)

	def test_it_narrows_to_an_organization_and_a_course(self):
		self.assertEqual(
			self._pairs(organization=self.department),
			{(self.in_department, self.course), (self.in_department, self.second)},
		)
		self.assertEqual(
			self._pairs(course=self.course),
			{(self.in_agency, self.course), (self.in_department, self.course)},
		)

	def test_an_organization_they_do_not_manage_is_refused(self):
		with self.assertRaises(frappe.PermissionError):
			get_organization_report(organization=self.other)

	def test_a_learner_without_organizations_is_refused(self):
		frappe.set_user(self.outside)
		with self.assertRaises(frappe.PermissionError):
			get_organization_report()
