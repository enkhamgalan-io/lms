from unittest.mock import patch

import frappe

from lms.lms.test_helpers import BaseTestUtils
from lms.lms.utils import get_discussion_replies, get_discussion_topics


class TestCourseForum(BaseTestUtils):
	"""A course's own forum is open to its enrolled learners and its instructors, and to no
	one else; a reply there notifies the topic's author and the instructors."""

	def setUp(self):
		super().setUp()
		h = frappe.generate_hash(length=6)
		self.instructor = self._create_user(f"cf-i-{h}@example.com", "Ina", "Instr", ["Course Creator"]).name
		self.learner = self._create_user(f"cf-l-{h}@example.com", "Lee", "Learner", ["LMS Student"]).name
		self.outsider = self._create_user(f"cf-o-{h}@example.com", "Otto", "Out", ["LMS Student"]).name
		self.course = self._create_course(f"Forum Course {h}", instructor=self.instructor).name
		self._create_enrollment(self.learner, self.course)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def as_user(self, user, fn, *args):
		frappe.set_user(user)
		try:
			return fn(*args)
		finally:
			frappe.set_user("Administrator")

	def open_topic(self, user, title="How do I start?"):
		def insert():
			topic = frappe.get_doc(
				{
					"doctype": "Discussion Topic",
					"title": title,
					"reference_doctype": "LMS Course",
					"reference_docname": self.course,
				}
			).insert()
			frappe.get_doc(
				{"doctype": "Discussion Reply", "topic": topic.name, "reply": "<p>Help</p>"}
			).insert()
			return topic.name

		return self.as_user(user, insert)

	def test_an_enrolled_learner_opens_a_topic_and_sees_it(self):
		topic = self.open_topic(self.learner)
		topics = self.as_user(self.learner, get_discussion_topics, "LMS Course", self.course)
		self.assertIn(topic, [row.name for row in topics])
		replies = self.as_user(self.instructor, get_discussion_replies, topic)
		self.assertEqual(len(replies), 1)

	def test_an_outsider_can_neither_read_nor_open_a_topic(self):
		with self.assertRaises(frappe.ValidationError):
			self.as_user(self.outsider, get_discussion_topics, "LMS Course", self.course)
		with self.assertRaises(frappe.PermissionError):
			self.open_topic(self.outsider)

	def test_a_reply_notifies_the_author_and_the_instructors(self):
		topic = self.open_topic(self.learner)
		with patch("lms.lms.utils.make_notification_logs") as notify:
			self.as_user(
				self.instructor,
				lambda: frappe.get_doc(
					{"doctype": "Discussion Reply", "topic": topic, "reply": "<p>Start here</p>"}
				).insert(),
			)
		notification, users = notify.call_args.args
		self.assertEqual(users, [self.learner])
		self.assertTrue(notification.link.endswith(f"courses/{self.course}#discussions"))
