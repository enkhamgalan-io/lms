import { afterEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { defineComponent, h } from 'vue'

vi.stubGlobal('__', (text: string) => text)
enableAutoUnmount(afterEach)

const { stub, batchDoc } = vi.hoisted(() => ({
	stub: { inheritAttrs: false, render: () => null },
	batchDoc: {
		name: 'B1',
		title: 'Batch',
		instructors: [],
		organizations: [{ organization: 'Agency' }] as { organization: string }[],
	},
}))

vi.mock('frappe-ui', () => ({
	createDocumentResource: () => ({
		doc: batchDoc,
		setValue: { submit: vi.fn() },
		reload: vi.fn(),
	}),
	createResource: () => ({ data: null, reload: vi.fn(), submit: vi.fn() }),
	toast: { success: vi.fn(), error: vi.fn() },
	call: vi.fn(),
	Combobox: stub,
	FormControl: stub,
}))
vi.mock('frappe-ui/experimental', () => ({
	InputLabel: stub,
	useInputLabeling: () => ({ inputId: 'id', labelId: 'label' }),
}))

// The organizations picker reports the names it was given and hands back new ones.
vi.mock('@/components/Controls/MultiLink.vue', () => ({
	default: defineComponent({
		props: ['label', 'modelValue'],
		emits: ['update:modelValue'],
		render() {
			return h('button', {
				'data-testid': `multilink-${this.label}`,
				'data-value': JSON.stringify(this.modelValue),
				onClick: () =>
					this.$emit('update:modelValue', ['Agency', 'Department']),
			})
		},
	}),
}))
for (const path of [
	'@/components/Controls/BooleanSwitch.vue',
	'@/components/Controls/Uploader.vue',
	'@/components/Controls/VideoPreviewField.vue',
	'@/components/Controls/Link.vue',
	'@/components/Controls/Select.vue',
	'@/components/RichTextEditor.vue',
	'@/components/Modals/NewMemberModal.vue',
	'@/pages/Batches/components/BatchCourses.vue',
	'@/pages/Batches/components/Assessments.vue',
]) {
	vi.doMock(path, () => ({ default: stub }))
}
vi.mock('@/utils', () => ({
	createLMSCategory: vi.fn(),
	getMetaInfo: vi.fn(),
	openSettings: vi.fn(),
	updateMetaInfo: vi.fn(),
}))
vi.mock('@/utils/batchForm', () => ({ validateBatch: vi.fn() }))
vi.mock('@/utils/format', () => ({ getDateFormat: () => 'YYYY-MM-DD' }))
vi.mock('@/utils/resource', () => ({ reportAutosaveError: vi.fn() }))
vi.mock('@/composables/useKeyboardShortcuts', () => ({
	useKeyboardShortcuts: vi.fn(),
	saveShortcut: vi.fn(),
}))
vi.mock('@/composables/useBatchForms', () => ({ openBatchForm: vi.fn() }))

const mountForm = async () => {
	const { default: BatchForm } = await import('@/pages/Batches/BatchForm.vue')
	const router = createRouter({
		history: createMemoryHistory(),
		routes: [{ path: '/', component: { render: () => null } }],
	})
	const wrapper = mount(BatchForm, {
		props: { batch: { data: { name: 'B1', can_manage: true } } },
		global: {
			plugins: [router],
			provide: { $user: { data: { name: 'ash@example.com' } } },
			mocks: { __: (text: string) => text },
		},
	})
	await flushPromises()
	return wrapper.find('[data-testid="multilink-Visible to organizations"]')
}

describe('the batch form organizations picker', () => {
	it('shows the organizations the batch is limited to by name', async () => {
		const picker = await mountForm()
		expect(JSON.parse(picker.attributes('data-value')!)).toEqual(['Agency'])
	})

	it('writes the names picked back as rows the server saves', async () => {
		const picker = await mountForm()
		await picker.trigger('click')
		expect(batchDoc.organizations).toEqual([
			{ organization: 'Agency' },
			{ organization: 'Department' },
		])
	})
})
