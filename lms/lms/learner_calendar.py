# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""A learner's own calendar: the live classes of their batches and the scheduled
quizzes meant for them, in the SPA and as an iCal feed a calendar app subscribes to."""

import hashlib
import hmac
from datetime import datetime, timedelta
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, get_datetime, get_system_timezone, get_url, now_datetime
from frappe.utils.password import get_encryption_key

from lms.lms.permissions import in_assessment_audience
from lms.lms.utils import get_lms_route

DEFAULT_MINUTES = 60
UTC = ZoneInfo("UTC")


@frappe.whitelist()
def get_my_calendar() -> list[dict]:
	return [{k: v for k, v in event.items() if k != "utc"} for event in _events(_logged_in_user())]


@frappe.whitelist()
def get_calendar_feed_url() -> str:
	"""The address a calendar app subscribes to. Anyone holding it reads the feed."""
	user = _logged_in_user()
	query = urlencode({"user": user, "token": _feed_token(user)})
	return get_url(f"/api/method/lms.lms.learner_calendar.get_calendar_feed?{query}")


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=120, seconds=60 * 60)
def get_calendar_feed(user: str, token: str):
	"""The iCal feed. Calendar apps send no session, so the signed token stands in for one."""
	if not (
		isinstance(user, str)
		and isinstance(token, str)
		and hmac.compare_digest(_feed_token(user), token)
		and frappe.db.get_value("User", user, "enabled")
	):
		frappe.throw(_("This calendar link is not valid."), frappe.PermissionError)

	frappe.local.response.filename = "lms-calendar.ics"
	frappe.local.response.filecontent = to_ics(_events(user))
	frappe.local.response.type = "download"


def _logged_in_user() -> str:
	if frappe.session.user == "Guest":
		frappe.throw(_("Log in to see your calendar."), frappe.PermissionError)
	return frappe.session.user


def _feed_token(user: str) -> str:
	# shortcut: derived from the site secret, so a leaked link cannot be revoked short of
	# rotating that secret; store a per-user salt once someone needs to revoke one.
	message = f"lms-calendar\0{user}".encode()
	return hmac.new(get_encryption_key().encode(), message, hashlib.sha256).hexdigest()


def _events(user: str) -> list[dict]:
	return _live_class_events(user) + _quiz_events(user)


def _live_class_events(user: str) -> list[dict]:
	batches = frappe.get_all("LMS Batch Enrollment", filters={"member": user}, pluck="batch")
	if not batches:
		return []
	classes = frappe.get_all(
		"LMS Live Class",
		filters={"batch_name": ("in", batches), "date": ("is", "set"), "time": ("is", "set")},
		fields=["name", "title", "date", "time", "duration", "timezone", "join_url", "batch_name"],
	)
	events = []
	for live_class in classes:
		start = get_datetime(f"{live_class.date} {live_class.time}")
		end = start + timedelta(minutes=cint(live_class.duration) or DEFAULT_MINUTES)
		events.append(
			_event(
				"live_class",
				live_class.name,
				live_class.title,
				start,
				end,
				live_class.timezone,
				url=live_class.join_url,
				batch=live_class.batch_name,
			)
		)
	return events


def _quiz_events(user: str) -> list[dict]:
	quizzes = frappe.get_all(
		"LMS Quiz",
		filters={"enable_scheduling": 1, "schedule_start": ("is", "set")},
		fields=["name", "title", "schedule_start", "schedule_end", "duration"],
	)
	events = []
	for quiz in quizzes:
		if not in_assessment_audience("LMS Quiz", quiz.name, user):
			continue
		start = get_datetime(quiz.schedule_start)
		end = (
			get_datetime(quiz.schedule_end)
			if quiz.schedule_end
			else start + timedelta(minutes=cint(quiz.duration) or DEFAULT_MINUTES)
		)
		events.append(
			_event(
				"quiz",
				quiz.name,
				quiz.title,
				start,
				end,
				get_system_timezone(),
				url=get_url(get_lms_route(f"quiz/{quiz.name}")),
			)
		)
	return events


def _event(kind, name, title, start, end, timezone, *, url=None, batch=None) -> dict:
	"""`start`/`end` are wall-clock times in `timezone`. The SPA draws them as they are,
	as the batch's own live class list does; the feed converts them to UTC."""
	try:
		zone = ZoneInfo(timezone or get_system_timezone())
	except (KeyError, ValueError):
		zone = ZoneInfo(get_system_timezone())
	return {
		"id": f"{kind}:{name}",
		"type": kind,
		"name": name,
		"title": title,
		"batch": batch,
		"url": url,
		"timezone": timezone,
		"fromDate": start.date().isoformat(),
		"toDate": end.date().isoformat(),
		"fromTime": start.strftime("%H:%M:%S"),
		"toTime": end.strftime("%H:%M:%S"),
		"utc": (start.replace(tzinfo=zone), end.replace(tzinfo=zone)),
	}


def to_ics(events: list[dict]) -> str:
	stamp = _ics_time(now_datetime().replace(tzinfo=ZoneInfo(get_system_timezone())))
	lines = [
		"BEGIN:VCALENDAR",
		"VERSION:2.0",
		"PRODID:-//Frappe Learning//Calendar//EN",
		"CALSCALE:GREGORIAN",
		f"X-WR-CALNAME:{_ics_text(_('Learning'))}",
	]
	for event in events:
		start, end = event["utc"]
		lines += [
			"BEGIN:VEVENT",
			f"UID:{_ics_text(event['id'])}@{frappe.local.site}",
			f"DTSTAMP:{stamp}",
			f"DTSTART:{_ics_time(start)}",
			f"DTEND:{_ics_time(end)}",
			f"SUMMARY:{_ics_text(event['title'] or '')}",
		]
		if event["url"]:
			lines.append(f"URL:{_ics_text(event['url'])}")
		lines.append("END:VEVENT")
	lines.append("END:VCALENDAR")
	return "".join(_fold(line) + "\r\n" for line in lines)


def _ics_time(value: datetime) -> str:
	return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _ics_text(value) -> str:
	"""RFC 5545 TEXT escaping."""
	return (
		str(value)
		.replace("\\", "\\\\")
		.replace(";", "\\;")
		.replace(",", "\\,")
		.replace("\r\n", "\\n")
		.replace("\n", "\\n")
	)


def _fold(line: str) -> str:
	"""RFC 5545: a line over 75 octets continues on the next, after one space, never
	splitting a multi-byte character (Mongolian titles are two bytes a letter)."""
	parts, chunk, limit = [], b"", 75
	for char in line:
		piece = char.encode()
		if len(chunk) + len(piece) > limit:
			parts.append(chunk.decode())
			chunk, limit = b"", 74
		chunk += piece
	parts.append(chunk.decode())
	return "\r\n ".join(parts)
