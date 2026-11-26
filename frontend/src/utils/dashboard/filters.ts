import type { BadgeProps } from 'frappe-ui'
import type {
	BatchFilter,
	PaymentStatus,
	StudentFilter,
	StudentSort,
	StudentStage,
	StudentTrack,
} from '@/types'

// The group a filter belongs to, or the filter on its own.
export const groupOf = <Filter extends string>(
	groups: Filter[][],
	filter: Filter
): Filter[] => groups.find((group) => group.includes(filter)) ?? [filter]

// Functions, so the label is translated when read rather than at import time,
// before the translations have loaded.
export const BATCH_FILTER_LABELS: Record<BatchFilter, () => string> = {
	on_track: () => __('On track'),
	behind: () => __('Behind'),
	at_risk: () => __('At risk'),
	not_started: () => __('Not started'),
	completed: () => __('Completed courses'),
	certified: () => __('Certified'),
	started: () => __('Started a course'),
	evaluation_requested: () => __('Evaluation requested'),
	no_evaluation: () => __('No evaluation yet'),
}

// Filters a card's filter can be swapped for from the student list, each
// filter in one group only so a card knows when the applied one is its own.
export const BATCH_FILTER_GROUPS: BatchFilter[][] = [
	['on_track', 'behind'],
	['at_risk', 'not_started'],
	['completed', 'no_evaluation', 'evaluation_requested'],
]

export const TRACK_LABELS: Record<StudentTrack, () => string> = {
	on_track: () => __('On track'),
	behind: () => __('Behind'),
	at_risk: () => __('At risk'),
	not_started: () => __('Not started'),
	completed: () => __('Completed'),
}

export const TRACK_THEMES: Record<StudentTrack, BadgeProps['theme']> = {
	on_track: 'green',
	behind: 'amber',
	at_risk: 'red',
	not_started: 'gray',
	completed: 'green',
}

export const STAGE_LABELS: Record<StudentStage, () => string> = {
	not_started: () => __('Not started'),
	in_progress: () => __('In progress'),
	completed: () => __('Completed'),
	certified: () => __('Certified'),
}

export const FILTER_LABELS: Record<StudentFilter, () => string> = {
	...STAGE_LABELS,
	completed: () => __('Completed, not certified'),
	inactive: () => __('Inactive 14+ days'),
	active: () => __('Active in the last 7 days'),
	started: () => __('Started a lesson'),
	halfway: () => __('Halfway or further'),
	finished: () => __('Finished all lessons'),
	evaluation_requested: () => __('Evaluation requested'),
}

export const FILTER_GROUPS: StudentFilter[][] = [
	['active', 'inactive'],
	['finished', 'completed'],
]

export const PAYMENT_LABELS: Record<PaymentStatus, () => string> = {
	Paid: () => __('Paid'),
	Pending: () => __('Pending'),
	Free: () => __('Free'),
}

export const PAYMENT_THEMES: Record<PaymentStatus, BadgeProps['theme']> = {
	Paid: 'green',
	Pending: 'amber',
	Free: 'gray',
}

// The dashboards' student sorts: get_course_students' and get_batch_students'
// sort_by. Null, the default, keeps newest enrollment first. A function, so the
// labels translate in the session's language.
export const studentSortChoices = (): {
	value: StudentSort
	label: string
}[] => [
	{ value: 'progress', label: __('Most progress') },
	{ value: 'views', label: __('Most lesson views') },
	{ value: 'enrollments', label: __('Most courses enrolled') },
]
