<template>
	<SettingsLayout
		:title="title"
		show-back
		:unsaved="isDirty"
		:save-label="__('Save')"
		:saving="saving"
		:can-save="isDirty"
		@back="emit('back')"
		@save="save"
	>
		<div v-if="doc" class="space-y-4">
			<div class="grid grid-cols-2 gap-4">
				<FormControl
					v-model="doc.organization_name"
					:label="__('Organization Name')"
					:description="
						isNew ? '' : __('The name is the record\'s id and cannot change.')
					"
					:disabled="!isNew"
					type="text"
					required
					autocomplete="off"
				/>
				<Link
					v-model="doc.parent_lms_organization"
					doctype="LMS Organization"
					:filters="{ is_group: 1 }"
					:label="__('Parent Organization')"
					:description="__('Leave empty for a top-level organization.')"
				/>
			</div>
			<FormControl
				v-model="doc.is_group"
				type="checkbox"
				:label="__('Has sub-organizations')"
				:description="
					__('Only a group can be picked as another organization\'s parent.')
				"
			/>
			<MultiLink
				v-model="managers"
				doctype="User"
				:label="__('Managers')"
				:description="
					__(
						'They become Organization Managers and handle the members of this organization and the ones under it.'
					)
				"
				:placeholder="__('Select users')"
			/>
			<ErrorMessage v-if="error" class="ms-1" :message="error" />
		</div>

		<div v-else class="flex flex-1 items-center justify-center py-20">
			<LoadingIndicator class="size-5 text-ink-gray-5" />
		</div>
	</SettingsLayout>
</template>
<script setup lang="ts">
import { ErrorMessage, FormControl, LoadingIndicator } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { cleanError } from '@/utils'
import { reloadSettingsLists } from '@/composables/useSettingsListResource'
import { useSettingsRecord } from '@/composables/useSettingsRecord'
import { runSave, useSaveState } from '@/composables/useSettingsSave'
import Link from '@/components/Controls/Link.vue'
import MultiLink from '@/components/Controls/MultiLink.vue'
import SettingsLayout from '@/components/Layouts/settings/desktop/SettingsLayout.vue'
import type { SettingsListRow } from '@/types'

const ORGANIZATION_DOCTYPE = 'LMS Organization'

const props = defineProps<{ name?: string | null }>()

const emit = defineEmits<{ back: [] }>()

const state = useSaveState()
const saving = state.saving
const error = state.error

const record = computed(() => props.name ?? null)
const pristine = ref('')
const snapshot = (value: SettingsListRow | null) =>
	JSON.stringify(value ?? null)

const { source, doc, isNew, isDirty } = useSettingsRecord({
	doctype: ORGANIZATION_DOCTYPE,
	record,
	dirty: (s) => (s.isNew ? snapshot(s.doc) !== pristine.value : s.isDirty),
})

watch(
	() => source.isNew,
	(seeding) => {
		if (!seeding || !doc.value) return
		Object.assign(doc.value, {
			organization_name: '',
			parent_lms_organization: '',
			is_group: 0,
			managers: [],
		})
		pristine.value = snapshot(doc.value)
	},
	{ flush: 'post', immediate: true }
)

const title = computed(() =>
	isNew.value
		? __('New Organization')
		: doc.value?.organization_name || __('Organization')
)

// MultiLink edits user ids; the doctype keeps them as LMS Organization Manager rows.
const managers = computed<string[]>({
	get: () =>
		(doc.value?.managers ?? []).map((row: SettingsListRow) => row.user),
	set: (users) => {
		if (doc.value) doc.value.managers = users.map((user) => ({ user }))
	},
})

const save = () => {
	if (!doc.value) return
	const wasNew = isNew.value
	return runSave(state, {
		validate: () =>
			doc.value?.organization_name ? '' : __('Organization Name is required'),
		run: () => source.save(),
		success: wasNew
			? __('Organization created successfully')
			: __('Organization updated successfully'),
		after: async () => {
			await reloadSettingsLists(ORGANIZATION_DOCTYPE)
			if (wasNew) emit('back')
		},
		failure: (err: any) =>
			cleanError(err?.messages?.[0] || err?.message || err) ||
			__('Error saving organization'),
	})
}
</script>
