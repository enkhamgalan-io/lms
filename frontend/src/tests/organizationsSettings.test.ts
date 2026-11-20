/**
 * Settings > Organizations: the tree is listed in nested-set order, so a child
 * follows its parent, and each row says where it sits and whether it is a group.
 */
import { describe, expect, it, vi } from 'vitest'
import type { SettingsListColumn } from '@/types'

vi.mock('@/components/Settings/rowActions', () => ({
	deleteRow: () => vi.fn(),
}))
vi.mock('@/components/Settings/Members/OrganizationForm.vue', () => ({
	default: { template: '<div />' },
}))

const { organizationsSettingsPage } = await import(
	'@/components/Settings/Members/organizations'
)

const column = (key: string) =>
	organizationsSettingsPage.columns.find(
		(c: SettingsListColumn) => c.key === key
	) as any

describe('organizations settings page', () => {
	it('lists the tree in nested-set order', () => {
		expect(organizationsSettingsPage.resource).toMatchObject({
			doctype: 'LMS Organization',
			orderBy: 'lft asc',
		})
	})

	it('names the parent, or says the organization is top level', () => {
		const name = column('organization_name')
		expect(name.secondary({ parent_lms_organization: 'Ministry' })).toBe(
			'Ministry'
		)
		expect(name.secondary({ parent_lms_organization: null })).toBe('Top level')
	})

	it('tells a group from a unit', () => {
		const type = column('is_group')
		expect(type.badges({ is_group: 1 })[0].label).toBe('Group')
		expect(type.badges({ is_group: 0 })[0].label).toBe('Unit')
	})
})
