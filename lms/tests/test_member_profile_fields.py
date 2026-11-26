import frappe

from lms.lms.api import get_member, get_profile_details, update_member
from lms.lms.test_helpers import BaseTestUtils


class TestMemberProfileFields(BaseTestUtils):
	"""Staff record a member's department, employee code and register number; the register
	number is checked, and stays off the profile other learners can open."""

	def setUp(self):
		super().setUp()
		h = frappe.generate_hash(length=6)
		self.moderator = self._create_user(f"mpf-mod-{h}@example.com", "Mo", "Derator", ["Moderator"]).name
		self.member = self._create_user(f"mpf-mem-{h}@example.com", "Bat", "Member", ["LMS Student"]).name
		self.peer = self._create_user(f"mpf-peer-{h}@example.com", "Peer", "Learner", ["LMS Student"]).name

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def update(self, profile):
		frappe.set_user(self.moderator)
		try:
			update_member(self.member, profile)
			return get_member(self.member)
		finally:
			frappe.set_user("Administrator")

	def test_staff_save_the_three_fields(self):
		row = self.update(
			{"department": "Хуулийн хэлтэс", "employee_code": "E-0042", "register_number": " уб90010112 "}
		)
		self.assertEqual(
			(row["department"], row["employee_code"], row["register_number"]),
			("Хуулийн хэлтэс", "E-0042", "УБ90010112"),
		)

	def test_a_malformed_register_number_is_refused(self):
		for value in ("UB90010112", "УБ9001011", "90010112УБ"):
			with self.subTest(value=value), self.assertRaises(frappe.ValidationError):
				self.update({"register_number": value})

	def test_another_learner_does_not_see_the_register_number(self):
		self.update({"register_number": "УБ90010112"})
		username = frappe.db.get_value("User", self.member, "username")
		frappe.set_user(self.peer)
		try:
			details = get_profile_details(username)
		finally:
			frappe.set_user("Administrator")
		self.assertNotIn("register_number", details)
