import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { reactive } from 'vue'
import dayjs from 'dayjs'

const resource = reactive<any>({ data: null, error: null, fetched: true })
const created: any[] = []
vi.mock('frappe-ui', () => ({
	createResource: (options: any) => {
		created.push(options)
		return resource
	},
}))

import ProfileHistory from '@/pages/ProfileHistory.vue'

const mountHistory = () =>
	mount(ProfileHistory, {
		props: { profile: { data: { username: 'bat' } } },
		global: {
			provide: { $dayjs: dayjs },
			mocks: { __: (globalThis as any).__ },
		},
	})

describe('the learning history tab', () => {
	it('asks for the profile owner and draws one row per course or batch', () => {
		resource.data = [
			{
				type: 'course',
				name: 'law-101',
				title: 'Үндсэн хууль',
				enrolled_on: '2026-09-01',
				completed_on: '2026-10-05',
				progress: 100,
				score: 90,
				credit_hours: 4,
				certificate: 'CERT-1',
			},
			{
				type: 'batch',
				name: 'b-1',
				title: 'Autumn batch',
				enrolled_on: '2026-08-01',
				completed_on: null,
				progress: null,
				score: null,
				credit_hours: 0,
				certificate: null,
			},
		]
		const rows = mountHistory().findAll(
			'[data-testid="learning-history"] tbody tr'
		)
		expect(created.at(-1).params).toEqual({ username: 'bat' })
		expect(rows).toHaveLength(2)
		expect(rows[0].text()).toContain('05 Oct 2026')
		expect(rows[0].text()).toContain('100%')
		expect(rows[0].text()).toContain('Issued')
		// Nothing to report shows a dash, not a zero.
		expect(
			rows[1]
				.findAll('td')
				.map((td) => td.text())
				.slice(2)
		).toEqual(['—', '—', '—', '—', '—'])
	})

	it('says so when there is nothing yet', () => {
		resource.data = []
		expect(mountHistory().text()).toContain('No courses or batches yet.')
	})
})
