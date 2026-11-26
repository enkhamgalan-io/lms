<template>
	<PageHeader :breadcrumbs="breadcrumbs" :loading="summary.loading">
		<template #actions>
			<HeaderButton
				variant="subtle"
				icon="lucide-download"
				:label="__('Download Excel')"
				@click="download"
			/>
		</template>
	</PageHeader>
	<div class="mx-auto w-full max-w-3xl space-y-4 p-5">
		<p v-if="summary.error" class="text-p-sm text-ink-red-5">
			{{ __('Could not load the results.') }}
		</p>
		<template v-else-if="summary.data">
			<p class="text-p-sm text-ink-gray-6" data-testid="results-responses">
				{{ __('{0} responses').format(responses) }} ·
				{{ __('Updates as answers come in') }}
			</p>
			<section
				v-for="(question, index) in summary.data"
				:key="question.question"
				class="rounded-6 border border-outline-gray-2 p-4"
				data-testid="results-question"
			>
				<h2 class="mb-3 text-base-medium text-ink-gray-9">
					{{ index + 1 }}. {{ question.question_detail }}
				</h2>
				<ul v-if="question.answers.length" class="space-y-2">
					<li v-for="answer in question.answers" :key="answer.answer">
						<div class="flex justify-between gap-3 text-p-sm text-ink-gray-8">
							<span class="min-w-0 break-words">{{ answer.answer }}</span>
							<span class="shrink-0 tabular-nums text-ink-gray-6">
								{{ answer.count }} · {{ share(answer.count) }}%
							</span>
						</div>
						<div
							class="mt-1 h-2 rounded-full bg-surface-gray-2"
							role="presentation"
						>
							<div
								class="h-2 rounded-full bg-surface-gray-10"
								:style="{ width: `${share(answer.count)}%` }"
							/>
						</div>
					</li>
				</ul>
				<p v-else class="text-p-sm italic text-ink-gray-6">
					{{ __('No answers yet.') }}
				</p>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { createResource, usePageMeta } from 'frappe-ui'
import { computed, inject, onUnmounted } from 'vue'
import HeaderButton from '@/components/HeaderButton.vue'
import PageHeader from '@/components/Layouts/pages/PageHeader.vue'

const props = defineProps<{ quizID: string }>()

const summary = createResource({
	url: 'lms.lms.doctype.lms_quiz.lms_quiz.get_quiz_summary',
	params: { quiz: props.quizID },
	auto: true,
})

// Every question carries the same count of submissions.
const responses = computed(() => summary.data?.[0]?.responses ?? 0)
const share = (count: number) =>
	responses.value ? Math.round((count * 1000) / responses.value) / 10 : 0

// Each answer pings this quiz's room with its name alone; the tally is re-read
// through get_quiz_summary, which keeps its own access check.
const socket = inject<any>('$socket', null)
const onUpdate = (data: { quiz?: string }) => {
	if (data?.quiz === props.quizID) summary.reload()
}
socket?.emit('doc_subscribe', 'LMS Quiz', props.quizID)
socket?.on('quiz_summary_updated', onUpdate)
onUnmounted(() => {
	socket?.off('quiz_summary_updated', onUpdate)
	socket?.emit('doc_unsubscribe', 'LMS Quiz', props.quizID)
})

const download = () => {
	window.location.href = `/api/method/lms.lms.doctype.lms_quiz.lms_quiz.download_quiz_summary?quiz=${encodeURIComponent(
		props.quizID
	)}`
}

const breadcrumbs = computed(() => [
	{ label: __('Quizzes'), route: { name: 'Quizzes' } },
	{
		label: props.quizID,
		route: { name: 'QuizForm', params: { quizID: props.quizID } },
	},
	{ label: __('Results') },
])

usePageMeta(() => ({ title: __('Results') }))
</script>
