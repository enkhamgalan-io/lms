import frappe

from lms.lms.api import add_member, get_member, get_members, save_role, set_member_enabled, update_member
from lms.lms.permissions import ORGANIZATION_MANAGER_ROLE
from lms.lms.test_helpers import BaseTestUtils


class TestOrganizationManagers(BaseTestUtils):
	"""An organization's managers run the people of that organization and of every
	organization under it, and no one else."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		hash = frappe.generate_hash(length=6)
		cls.ministry = cls._organization(f"Ministry {hash}", is_group=1)
		cls.agency = cls._organization(f"Agency {hash}", parent=cls.ministry, is_group=1)
		cls.department = cls._organization(f"Department {hash}", parent=cls.agency)
		cls.other_agency = cls._organization(f"Other Agency {hash}", parent=cls.ministry)

		cls.hr = cls._create_user(f"om-hr-{hash}@example.com", "Hana", "Hr", ["LMS Student"])
		cls.moderator = cls._create_user(f"om-mod-{hash}@example.com", "Mo", "Derator", ["Moderator"])
		cls.in_agency = cls._member(f"om-a-{hash}@example.com", cls.agency)
		cls.in_department = cls._member(f"om-d-{hash}@example.com", cls.department)
		cls.elsewhere = cls._member(f"om-b-{hash}@example.com", cls.other_agency)
		cls.unplaced = cls._member(f"om-n-{hash}@example.com", None)

		agency = frappe.get_doc("LMS Organization", cls.agency)
		agency.append("managers", {"user": cls.hr.name})
		agency.save()

	@classmethod
	def _organization(cls, name, parent=None, is_group=0):
		doc = frappe.get_doc(
			{
				"doctype": "LMS Organization",
				"organization_name": name,
				"parent_lms_organization": parent,
				"is_group": is_group,
			}
		).insert()
		return doc.name

	@classmethod
	def _member(cls, email, organization):
		user = cls._create_user(email, "Member", email.split("@")[0], ["LMS Student"])
		frappe.db.set_value("User", user.name, "organization", organization)
		return user.name

	def setUp(self):
		super().setUp()
		frappe.set_user(self.hr.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def _listed(self, **kwargs):
		return {row.name for row in get_members(limit_page_length=500, **kwargs)}

	def test_the_managers_table_grants_and_takes_back_the_role(self):
		self.assertIn(ORGANIZATION_MANAGER_ROLE, frappe.get_roles(self.hr.name))

		frappe.set_user("Administrator")
		department = frappe.get_doc("LMS Organization", self.department)
		department.append("managers", {"user": self.moderator.name})
		department.save()
		self.assertIn(ORGANIZATION_MANAGER_ROLE, frappe.get_roles(self.moderator.name))
		department.managers = []
		department.save()
		self.assertNotIn(ORGANIZATION_MANAGER_ROLE, frappe.get_roles(self.moderator.name))

	def test_the_list_holds_their_organizations_and_those_under_them(self):
		listed = self._listed()
		self.assertIn(self.in_agency, listed)
		self.assertIn(self.in_department, listed)
		self.assertNotIn(self.elsewhere, listed)
		self.assertNotIn(self.unplaced, listed)

	def test_a_moderator_still_sees_everyone(self):
		frappe.set_user(self.moderator.name)
		self.assertTrue({self.elsewhere, self.unplaced, self.in_department} <= self._listed())

	def test_rest_reads_of_user_are_narrowed_too(self):
		listed = set(frappe.get_list("User", pluck="name", limit_page_length=0))
		self.assertEqual(listed, {self.hr.name, self.in_agency, self.in_department})
		self.assertTrue(frappe.has_permission("User", doc=self.in_department))
		self.assertFalse(frappe.has_permission("User", doc=self.elsewhere))

	def test_only_their_organizations_can_be_picked(self):
		listed = set(frappe.get_list("LMS Organization", pluck="name"))
		self.assertEqual(listed, {self.agency, self.department})

	def test_people_outside_their_organizations_are_refused(self):
		for call in (
			lambda: get_member(self.elsewhere),
			lambda: update_member(self.elsewhere, {"designation": "Clerk"}),
			lambda: set_member_enabled(self.elsewhere, 0),
			lambda: save_role(self.unplaced, "LMS Student", 0),
		):
			with self.subTest(call=call), self.assertRaises(frappe.PermissionError):
				call()

	def test_a_member_cannot_be_handed_to_another_organization(self):
		with self.assertRaises(frappe.PermissionError):
			update_member(self.in_department, {"organization": self.other_agency})

		update_member(self.in_department, {"organization": self.agency, "designation": "Clerk", "rank": "II"})
		row = get_member(self.in_department)
		self.assertEqual((row.organization, row.designation, row.rank), (self.agency, "Clerk", "II"))

	def test_a_new_member_lands_in_one_of_their_organizations(self):
		email = f"om-new-{frappe.generate_hash(length=6)}@example.com"
		with self.assertRaises(frappe.PermissionError):
			add_member(email, "New", profile={})
		add_member(email, "New", profile={"organization": self.department})
		self.assertIn(email, self._listed())

	def test_they_grant_the_student_role_and_nothing_above_it(self):
		save_role(self.in_agency, "LMS Student", 1)
		with self.assertRaises(frappe.PermissionError):
			save_role(self.in_agency, "Course Creator", 1)
		self.assertNotIn("Course Creator", frappe.get_roles(self.in_agency))

	def test_a_disabled_member_moves_to_the_disabled_list(self):
		set_member_enabled(self.in_department, 0)
		self.assertNotIn(self.in_department, self._listed())
		self.assertIn(self.in_department, self._listed(status="Disabled"))
		set_member_enabled(self.in_department, 1)
		self.assertIn(self.in_department, self._listed())
