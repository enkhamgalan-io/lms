import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { reactive } from 'vue'

const { report } = vi.hoisted(() => ({
	report: {
		loading: false,
		reload: () => {},
		data: {
			courses: [{ value: 'C1', label: 'Law' }],
			rows: [
				{
					member: 'ada@example.com',
					full_name: 'Ada',
					organization: 'Agency',
					designation: 'Clerk',
					rank: 'II',
					course: 'C1',
					course_title: 'Law',
					progress: 100,
					quiz_average: 92.5,
					certificate: 'CERT-1',
					valid_until: null,
					access_expired: false,
				},
				{
					member: 'bo@example.com',
					full_name: 'Bo',
					organization: 'Department',
					designation: null,
					rank: null,
					course: 'C1',
					course_title: 'Law',
					progress: 40,
					quiz_average: null,
					certificate: null,
					valid_until: '2026-01-31',
					access_expired: true,
				},
			],
		},
	},
}))

vi.mock('frappe-ui', () => ({
	createResource: () => reactive(report),
	Badge: { props: ['label'], template: '<span>{{ label }}</span>' },
	Button: { template: '<button><slot /></button>' },
	LoadingIndicator: { template: '<span />' },
}))
vi.mock('@/components/Controls/Link.vue', () => ({
	default: { template: '<div />' },
}))
vi.mock('@/components/Controls/Select.vue', () => ({
	default: { template: '<div />' },
}))
vi.mock('@/components/Layouts/settings/desktop/SettingsLayout.vue', () => ({
	default: { template: '<div><slot name="header-actions" /><slot /></div>' },
}))

import OrganizationReport from '@/components/Settings/Members/OrganizationReport.vue'

const mountIt = () =>
	mount(OrganizationReport, {
		props: { label: 'Organization Report' },
		global: { mocks: { __: (text: string) => text } },
	})

describe('the organization report', () => {
	it('draws a row per enrollment with its results', () => {
		const rows = mountIt().findAll('tbody tr')
		expect(rows).toHaveLength(2)
		expect(rows[0].text()).toContain('Clerk · II')
		expect(rows[0].text()).toContain('92.5%')
		expect(rows[0].text()).toContain('Issued')
		expect(rows[1].text()).toContain('—')
	})

	it('counts people, enrollments, completions and certificates', () => {
		const stats = mountIt()
			.findAll('.tabular-nums.text-ink-gray-9')
			.map((stat) => stat.text())
		expect(stats).toEqual(['2', '2', '1', '1'])
	})

	it('marks an enrollment whose access has ended', () => {
		const expired = mountIt().find('tbody tr:last-child .text-ink-red-6')
		expect(expired.text()).toBe('2026-01-31')
	})
})
