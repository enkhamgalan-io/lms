<template>
	<section
		v-if="data && (data.completed || data.assessments.length)"
		class="mt-8 space-y-3 rounded-6 border border-outline-gray-2 p-4"
		:aria-label="__('Your progress')"
		data-testid="lesson-results"
	>
		<div class="flex items-center justify-between gap-2">
			<h2 class="text-base-semibold text-ink-gray-9">
				{{ __('Your progress') }}
			</h2>
			<Badge :theme="data.completed ? 'green' : 'gray'" size="md">
				{{ data.completed ? __('Lesson complete') : __('In progress') }}
			</Badge>
		</div>
		<ul v-if="data.assessments.length" class="divide-y divide-outline-gray-1">
			<li
				v-for="row in data.assessments"
				:key="`${row.type}:${row.name}`"
				class="flex items-center justify-between gap-3 py-2 text-p-sm"
			>
				<span class="truncate text-ink-gray-8">{{ row.title }}</span>
				<span class="flex shrink-0 items-center gap-2">
					<span
						v-if="row.score !== null && row.score !== undefined"
						class="tabular-nums text-ink-gray-7"
					>
						{{ row.score }}%
					</span>
					<span
						v-if="row.type === 'quiz' && row.attempts"
						class="text-ink-gray-6"
					>
						{{ __('{0} attempts').format(row.attempts) }}
					</span>
					<Badge :theme="status(row.status).theme">
						{{ status(row.status).label() }}
					</Badge>
				</span>
			</li>
		</ul>
	</section>
</template>
<script setup lang="ts">
import { Badge, createResource } from 'frappe-ui'
import { computed, watch } from 'vue'

type Status = 'passed' | 'failed' | 'to_review' | 'not_attempted'

interface LessonResult {
	type: 'quiz' | 'assignment' | 'exercise'
	name: string
	title: string
	status: Status
	score: number | null
	attempts: number
}

const props = defineProps<{ lesson: string }>()

const STATUSES: Record<Status, { theme: string; label: () => string }> = {
	passed: { theme: 'green', label: () => __('Passed') },
	failed: { theme: 'red', label: () => __('Failed') },
	to_review: { theme: 'orange', label: () => __('Awaiting review') },
	not_attempted: { theme: 'gray', label: () => __('Not attempted') },
}
const status = (value: Status) => STATUSES[value] ?? STATUSES.not_attempted

const results = createResource<{
	completed: boolean
	assessments: LessonResult[]
}>({
	url: 'lms.lms.api.get_my_lesson_results',
})
const data = computed(() => results.data)

// A failed load just leaves the panel hidden; the lesson itself is unaffected.
const reload = () => results.submit({ lesson: props.lesson }).catch(() => {})
watch(() => props.lesson, reload, { immediate: true })

defineExpose({ reload })
</script>
