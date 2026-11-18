<template>
	<div class="space-y-3" data-testid="member-enrollments">
		<div class="text-p-lg-semibold text-ink-gray-8">
			{{ __('Enrollments') }}
		</div>
		<div v-if="enrolled.length" class="flex flex-wrap gap-1.5">
			<Badge
				v-for="row in enrolled"
				:key="row.value"
				:label="row.label"
				theme="gray"
			/>
		</div>
		<div v-else-if="options.data" class="text-p-sm text-ink-gray-6">
			{{ __('Not enrolled in any course or batch yet.') }}
		</div>
		<div class="flex items-end gap-2">
			<FormControl
				v-model="picked"
				class="flex-1"
				type="select"
				:label="__('Enroll in')"
				:options="choices"
			/>
			<Button
				:label="__('Enroll')"
				:disabled="!picked"
				:loading="enrolling"
				@click="enroll"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import {
	Badge,
	Button,
	FormControl,
	call,
	createResource,
	toast,
} from 'frappe-ui'
import { computed, ref } from 'vue'
import { memberError } from '@/components/Settings/Members/members'

/**
 * The courses and batches a member is in, and the free ones open to them to
 * join. A Moderator or the member's Organization Manager enrolls them here;
 * get_member_enrollment_options already leaves out what the member may not join.
 */

type Option = { name: string; title: string; enrolled: boolean }

const props = defineProps<{ member: string }>()

const options = createResource<{ courses: Option[]; batches: Option[] }>({
	url: 'lms.lms.api.get_member_enrollment_options',
	params: { member: props.member },
	auto: true,
})

// One select for both kinds, so each value carries which endpoint it needs.
const rows = computed(() => [
	...(options.data?.courses ?? []).map((row) => ({
		value: `course:${row.name}`,
		label: __('Course: {0}').format(row.title),
		enrolled: row.enrolled,
	})),
	...(options.data?.batches ?? []).map((row) => ({
		value: `batch:${row.name}`,
		label: __('Batch: {0}').format(row.title),
		enrolled: row.enrolled,
	})),
])

const enrolled = computed(() => rows.value.filter((row) => row.enrolled))
const choices = computed(() => [
	{ label: __('Choose a course or batch'), value: '' },
	...rows.value.filter((row) => !row.enrolled),
])

const picked = ref('')
const enrolling = ref(false)

const enroll = async () => {
	const split = picked.value.indexOf(':')
	const kind = picked.value.slice(0, split)
	const name = picked.value.slice(split + 1)
	enrolling.value = true
	try {
		const result =
			kind === 'course'
				? await call('lms.lms.api.enroll_students_in_course', {
						course: name,
						members: [props.member],
				  })
				: await call('lms.lms.api.add_students_to_batch', {
						batch: name,
						members: [props.member],
				  })
		// The endpoints report a refused member in `errors` rather than failing.
		const refused = result?.errors?.[0]
		if (refused) {
			toast.error(refused.error || __('Could not enroll this member'))
			return
		}
		toast.success(__('Enrolled'))
		picked.value = ''
		options.reload()
	} catch (error: any) {
		toast.error(memberError(error, __('Could not enroll this member')))
	} finally {
		enrolling.value = false
	}
}
</script>
