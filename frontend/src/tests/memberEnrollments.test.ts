import { describe, expect, it, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { reactive } from 'vue'

const { callMock, toastMock, options } = vi.hoisted(() => ({
	callMock: vi.fn(),
	toastMock: { success: vi.fn(), error: vi.fn() },
	options: {
		data: {
			courses: [
				{ name: 'C1', title: 'Law', enrolled: true },
				{ name: 'C2', title: 'Ethics', enrolled: false },
			],
			batches: [{ name: 'B1', title: 'Spring', enrolled: false }],
		},
		reload: () => {},
	},
}))

vi.mock('frappe-ui', () => ({
	call: callMock,
	toast: toastMock,
	createResource: () => reactive(options),
	Badge: {
		props: ['label'],
		template: '<span class="badge">{{ label }}</span>',
	},
	Button: {
		props: ['label', 'disabled', 'loading'],
		template:
			'<button data-testid="enroll" :disabled="disabled">{{ label }}</button>',
	},
	FormControl: {
		props: ['modelValue', 'options', 'type', 'label'],
		emits: ['update:modelValue'],
		template: `<select :value="modelValue" @change="$emit('update:modelValue', $event.target.value)">
			<option v-for="o in options" :key="o.value" :value="o.value">{{ o.label }}</option>
		</select>`,
	},
}))
vi.mock('@/components/Settings/Members/members', () => ({
	memberError: (_error: unknown, fallback: string) => fallback,
}))

import MemberEnrollments from '@/components/Settings/Members/MemberEnrollments.vue'

const mountIt = () =>
	mount(MemberEnrollments, {
		props: { member: 'ada@example.com' },
		global: { mocks: { __: (text: string) => text } },
	})

beforeEach(() => {
	callMock.mockReset()
	toastMock.error.mockReset()
})

describe('a member’s enrollments', () => {
	it('lists what they are in and offers only the rest', () => {
		const wrapper = mountIt()
		expect(wrapper.find('.badge').text()).toBe('Course: Law')
		const offered = wrapper.findAll('option').map((o) => o.element.value)
		expect(offered).toEqual(['', 'course:C2', 'batch:B1'])
	})

	it('enrolls them in the course or batch picked', async () => {
		callMock.mockResolvedValue({ added: ['ada@example.com'], errors: [] })
		const wrapper = mountIt()
		await wrapper.get('select').setValue('batch:B1')
		await wrapper.get('[data-testid="enroll"]').trigger('click')
		await flushPromises()

		expect(callMock).toHaveBeenCalledWith('lms.lms.api.add_students_to_batch', {
			batch: 'B1',
			members: ['ada@example.com'],
		})
	})

	it('says why when the server refuses them', async () => {
		callMock.mockResolvedValue({
			added: [],
			errors: [{ member: 'ada@example.com', error: 'Not open to them' }],
		})
		const wrapper = mountIt()
		await wrapper.get('select').setValue('course:C2')
		await wrapper.get('[data-testid="enroll"]').trigger('click')
		await flushPromises()

		expect(toastMock.error).toHaveBeenCalledWith('Not open to them')
	})
})
