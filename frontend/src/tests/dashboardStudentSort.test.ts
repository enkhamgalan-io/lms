import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('frappe-ui', async () => {
	const { defineComponent, h } = await import('vue')
	const passthrough = { template: '<div><slot /></div>' }
	return {
		TextInput: passthrough,
		Button: defineComponent({
			setup(_, { slots }) {
				return () => h('button', slots.default?.())
			},
		}),
		// Each option as a button, so a test can read and pick them.
		Dropdown: defineComponent({
			props: ['options'],
			setup(props: { options: any[] }, { slots }) {
				return () =>
					h('div', { 'data-testid': 'dropdown' }, [
						slots.default?.(),
						...props.options.map((option) =>
							h(
								'button',
								{
									'data-option': option.label,
									'data-selected': String(Boolean(option.selected)),
									onClick: option.onClick,
								},
								option.label
							)
						),
					])
			},
		}),
	}
})
vi.mock('@/components/Dashboard/ChartCard.vue', () => ({
	default: { template: '<section><slot /></section>' },
}))

import DashboardStudentList from '@/components/Dashboard/DashboardStudentList.vue'

const SORTS = [
	{ value: 'progress', label: 'Most progress' },
	{ value: 'views', label: 'Most lesson views' },
]

const mountList = (props: Record<string, unknown> = {}) =>
	mount(DashboardStudentList, {
		props: {
			rows: [],
			total: 0,
			loading: false,
			columns: [],
			rowKey: 'enrollment',
			listKey: 'k',
			start: 0,
			listOptions: {},
			emptyDescription: '',
			filterLabel: null,
			search: '',
			pageLength: 20,
			...props,
		},
		global: {
			mocks: { __: (globalThis as any).__ },
			stubs: {
				ResponsiveListView: true,
				ListView: true,
				ListFooter: true,
				EmptyStateLayout: true,
				LoadError: true,
			},
		},
	})

describe('the students list sort', () => {
	it('offers the newest-first default and each order, checking the one applied', () => {
		const options = mountList({
			sortChoices: SORTS,
			sortValue: 'views',
		}).findAll('[data-option]')
		expect(options.map((option) => option.attributes('data-option'))).toEqual([
			'Newest enrollment',
			'Most progress',
			'Most lesson views',
		])
		expect(options.map((option) => option.attributes('data-selected'))).toEqual(
			['false', 'false', 'true']
		)
	})

	it('asks for the order picked, and null for the default', async () => {
		const wrapper = mountList({ sortChoices: SORTS, sortValue: 'views' })
		await wrapper.find('[data-option="Most progress"]').trigger('click')
		await wrapper.find('[data-option="Newest enrollment"]').trigger('click')
		expect(wrapper.emitted('chooseSort')).toEqual([['progress'], [null]])
	})

	it('shows no sort where none is offered, as on a batch', () => {
		expect(mountList().find('[data-testid="dropdown"]').exists()).toBe(false)
	})
})
