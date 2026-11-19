from unittest.mock import patch

import frappe
from frappe.utils import add_days, nowdate

from lms.lms import learner_calendar
from lms.lms.doctype.lms_live_class.lms_live_class import LMSLiveClass
from lms.lms.test_helpers import BaseTestUtils


class TestLearnerCalendar(BaseTestUtils):
	def setUp(self):
		super().setUp()
		self._create_user(
			"frappe@example.com", "Frappe", "Admin", ["Moderator", "Course Creator", "Batch Evaluator"]
		)
		self._create_evaluator()
		self.learner = self._create_user("cal-learner@example.com", "Cal", "Learner", ["LMS Student"])
		self.outsider = self._create_user("cal-outsider@example.com", "Cal", "Outsider", ["LMS Student"])

		course = self._create_course(title="Calendar Course")
		batch = self._create_batch(course.name, title="Calendar Batch")
		self._create_batch_enrollment(self.learner.name, batch.name)
		live_class = frappe.new_doc("LMS Live Class")
		live_class.update(
			{
				"title": "Calendar Live Class",
				"batch_name": batch.name,
				"date": add_days(nowdate(), 3),
				"time": "09:00:00",
				"duration": 90,
				"timezone": "Asia/Ulaanbaatar",
				"host": "Administrator",
				"join_url": "https://zoom.example/j/1",
			}
		)
		with patch.object(LMSLiveClass, "create_calendar_event"):
			live_class.insert()
		self.live_class = live_class

		questions = self._create_quiz_questions()
		self.quiz = self._create_quiz(questions, title="Calendar Quiz")
		self.quiz.update({"enable_scheduling": 1, "schedule_start": f"{add_days(nowdate(), 5)} 10:00:00"})
		self.quiz.save()
		self._place_in_lesson(course.name, "LMS Quiz", self.quiz.name)
		self._create_enrollment(self.learner.name, course.name)

		other = self._create_quiz(questions, title="Calendar Quiz Elsewhere")
		other.update({"enable_scheduling": 1, "schedule_start": f"{add_days(nowdate(), 5)} 10:00:00"})
		other.save()

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_a_learner_sees_their_live_classes_and_scheduled_quizzes(self):
		frappe.set_user(self.learner.name)
		events = {event["id"]: event for event in learner_calendar.get_my_calendar()}
		self.assertEqual(set(events), {f"live_class:{self.live_class.name}", f"quiz:{self.quiz.name}"})
		live = events[f"live_class:{self.live_class.name}"]
		self.assertEqual((live["fromTime"], live["toTime"]), ("09:00:00", "10:30:00"))
		self.assertEqual(live["url"], "https://zoom.example/j/1")

	def test_someone_else_sees_none_of_them(self):
		frappe.set_user(self.outsider.name)
		self.assertEqual(learner_calendar.get_my_calendar(), [])

	def test_the_feed_serves_ics_in_utc_for_a_valid_token(self):
		learner_calendar.get_calendar_feed(self.learner.name, learner_calendar._feed_token(self.learner.name))
		ics = frappe.local.response.filecontent
		self.assertTrue(ics.startswith("BEGIN:VCALENDAR\r\n"))
		self.assertEqual(ics.count("BEGIN:VEVENT"), 2)
		# 09:00 in Ulaanbaatar (UTC+8) is 01:00 UTC.
		day = add_days(nowdate(), 3).replace("-", "")
		self.assertIn(f"DTSTART:{day}T010000Z", ics)

	def test_the_feed_refuses_a_wrong_token(self):
		with self.assertRaises(frappe.PermissionError):
			learner_calendar.get_calendar_feed(
				self.learner.name, learner_calendar._feed_token(self.outsider.name)
			)

	def test_long_lines_fold_without_splitting_a_letter(self):
		line = "SUMMARY:" + "Монгол хэлний шалгалт " * 6
		folded = learner_calendar._fold(line)
		self.assertTrue(all(len(part.encode()) <= 75 for part in folded.split("\r\n")))
		self.assertEqual(folded.replace("\r\n ", ""), line)

	def test_text_is_escaped(self):
		self.assertEqual(learner_calendar._ics_text("a,b;c\\d\ne"), "a\\,b\\;c\\\\d\\ne")
