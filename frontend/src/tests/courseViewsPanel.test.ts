import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { reactive } from 'vue'

const { views } = vi.hoisted(() => ({
	views: {
		data: null as unknown,
		reload: vi.fn(),
		params: null as unknown,
	},
}))

vi.mock('frappe-ui', () => ({
	createResource: (options: { makeParams: () => unknown }) => {
		views.params = options.makeParams
		return reactive(views)
	},
	TabButtons: {
		props: ['modelValue', 'buttons'],
		emits: ['update:modelValue'],
		template: `<div><button v-for="b in buttons" :key="b.value" :data-testid="'tab-' + b.value" @click="$emit('update:modelValue', b.value)">{{ b.label }}</button></div>`,
	},
}))
vi.mock('frappe-ui/charts', () => ({
	ChartCard: { template: '<div><slot /></div>' },
	AreaChart: { template: '<div class="chart" />' },
}))
vi.mock('@/components/Dashboard/PanelSkeleton.vue', () => ({
	default: { template: '<div />' },
}))

String.prototype.format = function (this: string, ...args: unknown[]): string {
	return args.reduce<string>(
		(out, arg, i) => out.replaceAll(`{${i}}`, String(arg)),
		this
	)
}

import CourseViewsPanel from '@/pages/Courses/components/CourseViewsPanel.vue'

const mountWith = (data: unknown) => {
	views.data = data
	return mount(CourseViewsPanel, {
		props: { courseName: 'C1' },
		global: { mocks: { __: (text: string) => text } },
	})
}

describe('the course lesson views panel', () => {
	it('ranks the most opened lessons', () => {
		const wrapper = mountWith({
			series: [{ period: '2026-11-19', views: 5, viewers: 2 }],
			lessons: [
				{ lesson: 'L1', title: 'Ethics', views: 4, viewers: 2 },
				{ lesson: 'L2', title: 'Law', views: 1, viewers: 1 },
			],
		})
		const rows = wrapper.findAll('[data-testid="most-viewed"] li')
		expect(rows.map((row) => row.text())).toEqual([
			'Ethics4 views · 2 learners',
			'Law1 views · 1 learners',
		])
	})

	it('says so when nothing was opened', () => {
		const wrapper = mountWith({
			series: [{ period: '2026-11-19', views: 0, viewers: 0 }],
			lessons: [],
		})
		expect(wrapper.text()).toContain('No lesson has been opened in this time.')
		expect(wrapper.find('.chart').exists()).toBe(false)
	})

	it('asks for months once Months is picked', async () => {
		const wrapper = mountWith({ series: [], lessons: [] })
		await wrapper.get('[data-testid="tab-month"]').trigger('click')
		expect((views.params as () => { period: string })()).toEqual({
			course: 'C1',
			period: 'month',
		})
		expect(views.reload).toHaveBeenCalled()
	})
})
