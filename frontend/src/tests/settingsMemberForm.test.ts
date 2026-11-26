/**
 * Settings > Users > member form: adding and editing a member goes through the
 * members API (add_member, update_member), never a direct write on User, which
 * moderators do not have.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { computed, reactive, ref } from 'vue'

vi.stubGlobal('__', (text: string) => text)
enableAutoUnmount(afterEach)

const { callMock, toastMock, record } = vi.hoisted(() => ({
	callMock: vi.fn(),
	toastMock: { success: vi.fn(), error: vi.fn() },
	record: {
		doc: null as Record<string, unknown> | null,
		save: vi.fn(),
		reload: vi.fn(),
	},
}))

vi.mock('frappe-ui', () => ({
	call: callMock,
	toast: toastMock,
	createResource: () => ({ fetch: vi.fn() }),
	LoadingIndicator: { template: '<span />' },
	FormControl: {
		props: ['modelValue', 'label', 'disabled'],
		emits: ['update:modelValue'],
		template: `<input :data-testid="'field-' + label" :value="modelValue" :disabled="disabled" @input="$emit('update:modelValue', $event.target.value)" />`,
	},
}))

vi.mock('@/components/Layouts/settings/desktop/SettingsLayout.vue', () => ({
	default: {
		emits: ['save', 'back'],
		template: `<div><slot /><button data-testid="save" @click="$emit('save')" /></div>`,
	},
}))
vi.mock('@/components/Controls/RoleSwitches.vue', () => ({
	default: {
		emits: ['toggle'],
		template: `<button data-testid="role-student" @click="$emit('toggle', 'student', true)" />`,
	},
}))
vi.mock('@/components/Settings/Members/members', () => ({
	MEMBERS_DOCTYPE: 'User',
	ROLE_ROWS: [{ key: 'student', role: 'LMS Student' }],
	memberError: (_error: unknown, fallback: string) => fallback,
	canManageMembers: (user?: Record<string, boolean>) =>
		Boolean(user?.is_moderator || user?.is_organization_manager),
	grantableRoleRows: () => [{ key: 'student', role: 'LMS Student' }],
	noRoles: () => ({ student: false }),
	rolesFrom: () => ({}),
}))
vi.mock('@/components/Settings/Members/MemberEnrollments.vue', () => ({
	default: { template: '<div />' },
}))
vi.mock('@/components/Controls/Link.vue', () => ({
	default: { template: '<div />' },
}))
vi.mock('@/composables/useSettingsRecord', () => ({
	useSettingsRecord: () => {
		const source = reactive({
			isDirty: true,
			save: record.save,
			reload: record.reload,
		})
		const doc = ref(record.doc)
		return {
			source,
			doc: computed(() => doc.value),
			isDirty: computed(() => true),
		}
	},
}))
vi.mock('@framework/ui/components/Onboarding/index', () => ({
	useOnboarding: () => ({ updateOnboardingStep: vi.fn() }),
}))
vi.mock('@framework/ui/telemetry/index', () => ({
	useTelemetry: () => ({ capture: vi.fn() }),
}))
vi.mock('@/stores/members', () => ({ notifyMembersChanged: vi.fn() }))
vi.mock('@/utils', () => ({ sanitizeHTML: (html: string) => html }))

import MemberForm from '@/components/Settings/Members/MemberForm.vue'

const mountForm = (
	name: string,
	user: Record<string, boolean> = { is_moderator: true }
) =>
	mount(MemberForm, {
		props: { name },
		global: {
			mocks: { __: (text: string) => text },
			provide: { $user: { data: user } },
		},
	})

beforeEach(() => {
	callMock.mockReset()
	record.save.mockReset()
	record.reload.mockReset()
})

describe('Settings member form', () => {
	it('adds a member and its profile in one add_member call', async () => {
		record.doc = reactive({
			email: ' ada@example.com ',
			first_name: 'Ada',
			last_name: 'Lovelace',
			phone: '123',
		})
		callMock.mockResolvedValueOnce({ name: 'ada@example.com' })
		const w = mountForm('new')
		await w.get('[data-testid="save"]').trigger('click')
		await flushPromises()

		expect(callMock).toHaveBeenCalledTimes(1)
		expect(callMock).toHaveBeenCalledWith('lms.lms.api.add_member', {
			email: 'ada@example.com',
			first_name: 'Ada',
			last_name: 'Lovelace',
			profile: {
				first_name: 'Ada',
				last_name: 'Lovelace',
				username: null,
				phone: '123',
				mobile_no: null,
				location: null,
				bio: null,
				organization: null,
				designation: null,
				rank: null,
				department: null,
				employee_code: null,
				register_number: null,
			},
		})
		expect(record.save).not.toHaveBeenCalled()
		expect(toastMock.success).toHaveBeenCalled()
	})

	it('finishes the added member on a retry instead of adding it again', async () => {
		record.doc = reactive({ email: 'ada@example.com', first_name: 'Ada' })
		callMock
			.mockResolvedValueOnce({ name: 'ada@example.com' }) // add_member
			.mockRejectedValueOnce(new Error('role refused')) // save_role
			.mockResolvedValue({ name: 'ada@example.com' })
		const w = mountForm('new')
		await w.get('[data-testid="role-student"]').trigger('click')
		await w.get('[data-testid="save"]').trigger('click')
		await flushPromises()
		expect(record.doc.email).toBe('ada@example.com')
		// The account exists now, so its address can no longer change.
		expect(
			w.get('[data-testid="field-Email"]').attributes('disabled')
		).toBeDefined()

		await w.get('[data-testid="save"]').trigger('click')
		await flushPromises()

		const methods = callMock.mock.calls.map(([method]) => method)
		expect(methods).toEqual([
			'lms.lms.api.add_member',
			'lms.lms.api.save_role',
			'lms.lms.api.update_member',
			'lms.lms.api.save_role',
		])
		expect(callMock).toHaveBeenNthCalledWith(
			3,
			'lms.lms.api.update_member',
			expect.objectContaining({ member: 'ada@example.com' })
		)
		expect(w.emitted('back')).toHaveLength(1)
	})

	it('unlocks the email again once the form moves to another record', async () => {
		record.doc = reactive({ email: 'ada@example.com', first_name: 'Ada' })
		callMock
			.mockResolvedValueOnce({ name: 'ada@example.com' }) // add_member
			.mockRejectedValueOnce(new Error('role refused')) // save_role
		const w = mountForm('new')
		await w.get('[data-testid="role-student"]').trigger('click')
		await w.get('[data-testid="save"]').trigger('click')
		await flushPromises()
		expect(
			w.get('[data-testid="field-Email"]').attributes('disabled')
		).toBeDefined()

		await w.setProps({ name: 'bob@example.com' })
		await w.setProps({ name: 'new' })
		expect(
			w.get('[data-testid="field-Email"]').attributes('disabled')
		).toBeUndefined()
	})

	it('saves an edited member through update_member and reloads it', async () => {
		record.doc = reactive({
			name: 'ada@example.com',
			email: 'ada@example.com',
			first_name: 'Ada',
			last_name: 'King',
		})
		callMock.mockResolvedValue({ name: 'ada@example.com' })
		const w = mountForm('ada@example.com')
		await w.get('[data-testid="save"]').trigger('click')
		await flushPromises()

		expect(callMock).toHaveBeenCalledWith(
			'lms.lms.api.update_member',
			expect.objectContaining({
				member: 'ada@example.com',
				profile: expect.objectContaining({ last_name: 'King' }),
			})
		)
		expect(callMock).not.toHaveBeenCalledWith(
			'lms.lms.api.add_member',
			expect.anything()
		)
		expect(record.save).not.toHaveBeenCalled()
		expect(record.reload).toHaveBeenCalled()
	})

	it('closes an edited member only once the reload has finished', async () => {
		record.doc = reactive({ name: 'ada@example.com', first_name: 'Ada' })
		let finishReload = () => {}
		record.reload.mockReturnValue(
			new Promise<void>((resolve) => (finishReload = resolve))
		)
		callMock.mockResolvedValue({ name: 'ada@example.com' })
		const w = mountForm('ada@example.com')
		await w.get('[data-testid="save"]').trigger('click')
		await flushPromises()

		expect(w.emitted('back')).toBeUndefined()
		finishReload()
		await flushPromises()
		expect(w.emitted('back')).toHaveLength(1)
	})

	it('keeps an Organization Manager from adding a member with no organization', async () => {
		record.doc = reactive({ email: 'ada@example.com', first_name: 'Ada' })
		const w = mountForm('new', { is_organization_manager: true })
		await w.get('[data-testid="save"]').trigger('click')
		await flushPromises()

		expect(callMock).not.toHaveBeenCalled()

		record.doc = reactive({
			email: 'ada@example.com',
			first_name: 'Ada',
			organization: 'Agency',
		})
		callMock.mockResolvedValue({ name: 'ada@example.com' })
		const placed = mountForm('new', { is_organization_manager: true })
		await placed.get('[data-testid="save"]').trigger('click')
		await flushPromises()

		expect(callMock).toHaveBeenCalledWith(
			'lms.lms.api.add_member',
			expect.objectContaining({
				profile: expect.objectContaining({ organization: 'Agency' }),
			})
		)
	})
})
