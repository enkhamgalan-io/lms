import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { reactive } from 'vue'

const summary = reactive<any>({
	data: [
		{
			question: 'Q-1',
			question_detail: 'Which do you prefer?',
			responses: 3,
			answers: [
				{ answer: 'Tea', count: 2 },
				{ answer: 'Coffee', count: 1 },
			],
		},
	],
	error: null,
	loading: false,
	reload: vi.fn(),
})
vi.mock('frappe-ui', () => ({
	createResource: () => summary,
	usePageMeta: () => {},
}))

import QuizResults from '@/pages/QuizResults.vue'

const fakeSocket = () => {
	const handlers: Record<string, (data: any) => void> = {}
	return {
		handlers,
		emit: vi.fn(),
		on: vi.fn((event: string, handler: any) => (handlers[event] = handler)),
		off: vi.fn(),
	}
}

const mountResults = (socket: ReturnType<typeof fakeSocket>) =>
	mount(QuizResults, {
		props: { quizID: 'staff-survey' },
		global: {
			provide: { $socket: socket },
			mocks: { __: (globalThis as any).__ },
			stubs: { PageHeader: true, HeaderButton: true },
		},
	})

describe('the survey results page', () => {
	it('shows each answer with its count and share of the responses', () => {
		const text = mountResults(fakeSocket()).text()
		expect(text).toContain('3 responses')
		expect(text).toContain('Tea')
		expect(text).toContain('2 · 66.7%')
		expect(text).toContain('1 · 33.3%')
	})

	it("re-reads the tally when this quiz's room is pinged, and leaves the room on exit", () => {
		const socket = fakeSocket()
		const wrapper = mountResults(socket)
		expect(socket.emit).toHaveBeenCalledWith(
			'doc_subscribe',
			'LMS Quiz',
			'staff-survey'
		)

		socket.handlers.quiz_summary_updated({ quiz: 'another-quiz' })
		expect(summary.reload).not.toHaveBeenCalled()
		socket.handlers.quiz_summary_updated({ quiz: 'staff-survey' })
		expect(summary.reload).toHaveBeenCalledTimes(1)

		wrapper.unmount()
		expect(socket.off).toHaveBeenCalledWith(
			'quiz_summary_updated',
			socket.handlers.quiz_summary_updated
		)
		expect(socket.emit).toHaveBeenCalledWith(
			'doc_unsubscribe',
			'LMS Quiz',
			'staff-survey'
		)
	})
})
