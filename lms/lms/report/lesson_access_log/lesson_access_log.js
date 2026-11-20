// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.query_reports["Lesson Access Log"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(
				frappe.datetime.get_today(),
				-1
			),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "course",
			label: __("Course"),
			fieldtype: "Link",
			options: "LMS Course",
		},
		{
			fieldname: "member",
			label: __("Member"),
			fieldtype: "Link",
			options: "User",
		},
		{
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: ["Day", "Month"],
			default: "Day",
		},
	],
};
