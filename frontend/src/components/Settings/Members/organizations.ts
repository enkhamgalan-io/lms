import { markRaw } from 'vue'
import { deleteRow } from '@/components/Settings/rowActions'
import OrganizationForm from '@/components/Settings/Members/OrganizationForm.vue'
import type { ListPage } from '@/types/settingsSchema'
import type { SettingsListColumn } from '@/types'

/**
 * Settings > Organizations, as config. LMS Organization is a nested set, so
 * ordering by `lft` lists every organization right after its parent.
 */

export const ORGANIZATION_DOCTYPE = 'LMS Organization'

const removeOrganization = deleteRow(
	ORGANIZATION_DOCTYPE,
	'Organization deleted successfully',
	'Error deleting organization'
)

// Every header is a getter: `__` is installed after this module is evaluated.
const columns: SettingsListColumn[] = [
	{
		key: 'organization_name',
		get label() {
			return __('Organization')
		},
		type: 'stacked',
		width: 'minmax(0, 1.6fr)',
		primary: (row) => row.organization_name,
		secondary: (row) => row.parent_lms_organization || __('Top level'),
	},
	{
		key: 'is_group',
		get label() {
			return __('Type')
		},
		type: 'badge',
		badges: (row) => [
			{
				label: row.is_group ? __('Group') : __('Unit'),
				theme: 'gray',
			},
		],
	},
	{
		key: 'actions',
		type: 'actions',
		ariaLabel: (row) => __('Actions for {0}').format(row.organization_name),
		options: (row) => [
			{
				label: __('Delete'),
				icon: 'lucide-trash-2',
				theme: 'red',
				onClick: () => removeOrganization(row),
			},
		],
	},
]

const form = markRaw(OrganizationForm)

export const organizationsSettingsPage: ListPage = {
	kind: 'list',
	resource: {
		doctype: ORGANIZATION_DOCTYPE,
		fields: [
			'name',
			'organization_name',
			'parent_lms_organization',
			'is_group',
		],
		searchFields: ['organization_name'],
		orderBy: 'lft asc',
	},
	columns,
	searchable: true,
	empty: { name: 'Organizations', icon: 'lucide-network' },
	create: { detail: { kind: 'custom', component: form } },
	rowDetail: { kind: 'custom', component: form },
}
