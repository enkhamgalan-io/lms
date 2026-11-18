/** What `lms.lms.utils.get_quiz_with_questions` returns, as the quiz card reads it. */

export type QuizQuestionType = 'Choices' | 'User Input' | 'Open Ended'

/** One LMS Question. `option_N` / `explanation_N` run from 1 to 10. */
export type QuizQuestionDetails = {
	name: string
	question: string
	type: QuizQuestionType
	multiple?: 0 | 1
	// Option numbers in display order, sent when the quiz shuffles its options.
	option_order?: number[]
} & {
	[key: `option_${number}` | `explanation_${number}`]: string | null | undefined
}

/** A row of the quiz's question table. */
export interface QuizQuestionRow {
	name?: string
	question: string
	marks?: number
	// Copied from the question when the quiz is saved.
	type?: QuizQuestionType
}

export interface QuizDetails {
	name: string
	title: string
	duration: number
	questions?: QuizQuestionRow[]
	passing_percentage?: number
	max_attempts?: number
	show_answers?: 0 | 1
	show_submission_history?: 0 | 1
	shuffle_questions?: 0 | 1
	limit_questions_to?: number
	shuffle_options?: 0 | 1
	single_session?: 0 | 1
	quiz_type?: 'Quiz' | 'Survey' | 'Poll'
	is_anonymous?: 0 | 1
	// Sent for a single-session quiz; only the window holding it may submit.
	attempt_token?: string
	enable_proctoring?: 0 | 1
	max_violations: number
	enable_negative_marking?: 0 | 1
	marks_to_cut?: number
	enable_scheduling?: 0 | 1
	schedule_start?: string | null
	schedule_start_iso?: string | null
	schedule_end?: string | null
	schedule_end_iso?: string | null
}

export interface QuizWithQuestions {
	quiz?: QuizDetails
	questions_by_name?: Record<string, QuizQuestionDetails>
}

/** A past attempt, as the history list shows it. A type, not an interface, so it
 * passes as a ResponsiveListView row. */
export type QuizAttempt = {
	name: string
	creation: string
	score: number
	score_out_of: number
	percentage: number
	passing_percentage: number
	idx?: number
}

/** What `lms_quiz.submit_quiz` returns. */
export interface QuizSubmissionResult {
	submission?: string
	is_open_ended?: boolean | 0 | 1
	percentage: number
	score: number
	score_out_of: number
	pass?: boolean
	correct?: number
	wrong?: number
	unanswered?: number
	/** Set for a survey or poll, which comes back with no score. */
	quiz_type?: 'Survey' | 'Poll'
	/** A poll's answers so far, summed up per question. */
	summary?: QuizSummaryQuestion[] | null
}

export interface QuizSummaryQuestion {
	question: string
	question_detail: string
	answers: { answer: string; count: number }[]
	responses: number
}

/** 1 correct, 2 partially correct, 0 wrong; undefined for an untouched option. */
export type AnswerVerdict = 0 | 1 | 2 | undefined

/** A learner's answer to one question, as kept in localStorage until submit. */
export interface SavedAnswer {
	question_name: string
	answer: (string | null | undefined)[]
}

export type ViolationSeverity = 'violation' | 'warning'

/** A proctoring event as the card lists it. */
export interface ViolationEvent {
	eventType: string
	severity: ViolationSeverity
	timestamp: string
	frame: string | null
	/** Seconds into the attempt, for an event this page saw happen. */
	elapsed?: number
}

/** A proctoring event as `get_quiz_violation_logs` stores it. */
export interface StoredViolationRow {
	event_type: string
	severity: ViolationSeverity
	timestamp: string
	frame: string | null
}
