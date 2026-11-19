import frappe

from lms.lms.api import get_profile_details
from lms.lms.doctype.lms_certificate.lms_certificate import get_default_certificate_template
from lms.lms.doctype.lms_credit_entry.lms_credit_entry import total_credit_hours
from lms.lms.doctype.lms_enrollment.lms_enrollment import update_enrollment
from lms.lms.test_helpers import BaseTestUtils


class TestCreditHours(BaseTestUtils):
	def setUp(self):
		super().setUp()
		self._create_user(
			"frappe@example.com", "Frappe", "Admin", ["Moderator", "Course Creator", "Batch Evaluator"]
		)
		self._create_evaluator()
		self.learner = self._create_user("cr-learner@example.com", "Credit", "Learner", ["LMS Student"])
		self.other = self._create_user("cr-other@example.com", "Other", "Learner", ["LMS Student"])
		self.course = self._create_course(title="Credit Course")
		frappe.db.set_value("LMS Course", self.course.name, "credit_hours", 4.5)
		self.enrollment = self._create_enrollment(self.learner.name, self.course.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def entries(self, member=None):
		return frappe.get_all(
			"LMS Credit Entry",
			filters={"member": member or self.learner.name},
			fields=["source_type", "source", "hours"],
		)

	def test_completing_a_course_credits_its_hours_once(self):
		update_enrollment(self.enrollment.name, {"progress": 50})
		self.assertEqual(self.entries(), [])

		update_enrollment(self.enrollment.name, {"progress": 100})
		update_enrollment(self.enrollment.name, {"progress": 99})
		update_enrollment(self.enrollment.name, {"progress": 100})
		self.assertEqual(
			[(e.source_type, e.source, e.hours) for e in self.entries()],
			[("LMS Course", self.course.name, 4.5)],
		)

	def test_a_course_without_credit_hours_credits_nothing(self):
		frappe.db.set_value("LMS Course", self.course.name, "credit_hours", 0)
		update_enrollment(self.enrollment.name, {"progress": 100})
		self.assertEqual(self.entries(), [])

	def test_a_batch_certificate_credits_the_batch(self):
		batch = self._create_batch(self.course.name, title="Credit Batch")
		frappe.db.set_value("LMS Batch", batch.name, "credit_hours", 2)
		self._create_batch_enrollment(self.learner.name, batch.name)
		certificate = frappe.new_doc("LMS Certificate")
		certificate.update(
			{
				"batch_name": batch.name,
				"member": self.learner.name,
				"issue_date": frappe.utils.nowdate(),
				"template": get_default_certificate_template(),
			}
		)
		certificate.insert()
		self.assertEqual(
			[(e.source_type, e.source, e.hours) for e in self.entries()],
			[("LMS Batch", batch.name, 2)],
		)

	def test_a_second_entry_for_the_same_source_is_refused(self):
		update_enrollment(self.enrollment.name, {"progress": 100})
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "LMS Credit Entry",
					"member": self.learner.name,
					"source_type": "LMS Course",
					"source": self.course.name,
					"hours": 1,
				}
			).insert()

	def test_the_total_shows_on_your_own_profile_only(self):
		update_enrollment(self.enrollment.name, {"progress": 100})
		self.assertEqual(total_credit_hours(self.learner.name), 4.5)
		username = frappe.db.get_value("User", self.learner.name, "username")

		frappe.set_user(self.learner.name)
		self.assertEqual(get_profile_details(username).credit_hours, 4.5)
		frappe.set_user(self.other.name)
		self.assertNotIn("credit_hours", get_profile_details(username))
