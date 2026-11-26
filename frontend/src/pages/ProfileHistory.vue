<template>
	<div class="mt-7 mb-10">
		<h2 class="mb-3 text-lg-semibold text-ink-gray-9">
			{{ __('Learning history') }}
		</h2>
		<p v-if="history.error" class="text-p-sm text-ink-red-5">
			{{ __('Could not load the learning history.') }}
		</p>
		<div
			v-else-if="history.data?.length"
			class="overflow-x-auto rounded-6 border border-outline-gray-2"
		>
			<table class="w-full text-p-sm" data-testid="learning-history">
				<thead class="bg-surface-gray-1 text-ink-gray-6">
					<tr>
						<th scope="col" class="px-3 py-2 text-start font-medium">
							{{ __('Course or batch') }}
						</th>
						<th scope="col" class="px-3 py-2 text-start font-medium">
							{{ __('Enrolled') }}
						</th>
						<th scope="col" class="px-3 py-2 text-start font-medium">
							{{ __('Completed') }}
						</th>
						<th scope="col" class="px-3 py-2 text-end font-medium">
							{{ __('Progress') }}
						</th>
						<th scope="col" class="px-3 py-2 text-end font-medium">
							{{ __('Score') }}
						</th>
						<th scope="col" class="px-3 py-2 text-end font-medium">
							{{ __('Credit hours') }}
						</th>
						<th scope="col" class="px-3 py-2 text-start font-medium">
							{{ __('Certificate') }}
						</th>
					</tr>
				</thead>
				<tbody class="text-ink-gray-8">
					<tr
						v-for="row in history.data"
						:key="`${row.type}-${row.name}`"
						class="border-t border-outline-gray-1"
					>
						<td class="px-3 py-2">
							<div class="font-medium text-ink-gray-9">{{ row.title }}</div>
							<div class="text-ink-gray-6">
								{{ row.type === 'batch' ? __('Batch') : __('Course') }}
							</div>
						</td>
						<td class="whitespace-nowrap px-3 py-2">
							{{ formatDate(row.enrolled_on) }}
						</td>
						<td class="whitespace-nowrap px-3 py-2">
							{{ formatDate(row.completed_on) }}
						</td>
						<td class="px-3 py-2 text-end tabular-nums">
							{{ row.progress == null ? '—' : `${Math.round(row.progress)}%` }}
						</td>
						<td class="px-3 py-2 text-end tabular-nums">
							{{ row.score == null ? '—' : row.score }}
						</td>
						<td class="px-3 py-2 text-end tabular-nums">
							{{ row.credit_hours || '—' }}
						</td>
						<td class="px-3 py-2">
							<span v-if="row.certificate" class="text-ink-green-4">
								{{ __('Issued') }}
							</span>
							<span v-else class="text-ink-gray-6">—</span>
						</td>
					</tr>
				</tbody>
			</table>
		</div>
		<div v-else-if="history.fetched" class="text-sm italic text-ink-gray-6">
			{{ __('No courses or batches yet.') }}
		</div>
	</div>
</template>
<script setup>
import { createResource } from 'frappe-ui'
import { inject } from 'vue'

const dayjs = inject('$dayjs')
const props = defineProps({
	profile: {
		type: Object,
		required: true,
	},
})

const history = createResource({
	url: 'lms.lms.api.get_learning_history',
	params: { username: props.profile.data?.username },
	auto: Boolean(props.profile.data?.username),
})

const formatDate = (value) => (value ? dayjs(value).format('DD MMM YYYY') : '—')
</script>
