import type { SelectOption } from '@/types/settingsSchema'

/**
 * What a course or batch may require of each item before a lesson counts as
 * complete. Empty follows the level above: the site, then the course.
 * course_lesson.get_completion_rules reads the same three fields.
 *
 * Functions, not constants: `__` is installed after modules are imported.
 */
export const completionFields = () =>
	[
		{ name: 'quiz_completion', label: __('Quizzes to complete a lesson') },
		{
			name: 'assignment_completion',
			label: __('Assignments to complete a lesson'),
		},
		{
			name: 'programming_exercise_completion',
			label: __('Programming exercises to complete a lesson'),
		},
	] as const

export const completionOptions = (): SelectOption[] => [
	{ label: __('Follow the level above'), value: '' },
	{ label: __('Not required'), value: 'Not required' },
	{ label: __('Attempt it'), value: 'Attempted' },
	{ label: __('Pass it'), value: 'Passed' },
]
