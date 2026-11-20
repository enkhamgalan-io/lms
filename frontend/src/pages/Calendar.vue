<template>
	<div class="flex h-full flex-col">
		<PageHeader :breadcrumbs="breadcrumbs">
			<template #actions>
				<Button
					variant="subtle"
					:loading="feedUrl.loading"
					@click="copyFeedUrl"
				>
					<template #prefix>
						<span class="lucide-link size-4" />
					</template>
					{{ __('Subscribe') }}
				</Button>
			</template>
		</PageHeader>
		<div v-if="loadError" class="p-5">
			<EmptyStateLayout
				:name="__('Calendar')"
				icon="lucide-calendar-x-2"
				width="lg"
				:title="__('Could not load your calendar')"
				:description="__('The request did not get through. Try again.')"
			>
				<Button
					variant="subtle"
					:loading="events.loading"
					@click="events.reload()"
				>
					{{ __('Retry') }}
				</Button>
			</EmptyStateLayout>
		</div>
		<div v-else-if="events.fetched && !events.data?.length" class="p-5">
			<EmptyStateLayout
				:name="__('Calendar')"
				icon="lucide-calendar"
				width="lg"
				:title="__('Nothing scheduled')"
				:description="
					__(
						'Live classes of your batches and scheduled quizzes will show up here.'
					)
				"
			/>
		</div>
		<div v-else class="flex min-h-0 flex-1 flex-col overflow-hidden p-5">
			<Calendar
				v-if="events.data?.length"
				:config="calendarConfig"
				:events="events.data"
				@click="(event) => openEvent(event.calendarEvent)"
			>
				<template #header="{ currentMonthYear, decrement, increment }">
					<div class="mb-2 flex justify-between">
						<span class="text-lg-semibold text-ink-gray-9">
							{{ currentMonthYear }}
						</span>
						<div class="flex gap-x-1">
							<Button
								@click="decrement()"
								variant="ghost"
								:label="__('Previous')"
							>
								<template #icon>
									<span class="lucide-chevron-left size-4 rtl:rotate-180" />
								</template>
							</Button>
							<Button @click="increment()" variant="ghost" :label="__('Next')">
								<template #icon>
									<span class="lucide-chevron-right size-4 rtl:rotate-180" />
								</template>
							</Button>
						</div>
					</div>
				</template>
			</Calendar>
		</div>
	</div>
</template>
<script setup>
import { Button, createResource, toast } from 'frappe-ui'
import { Calendar } from 'frappe-ui/experimental'
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '@/components/Layouts/pages/PageHeader.vue'
import EmptyStateLayout from '@/components/Layouts/EmptyStateLayout.vue'
import { copyText } from '@/utils/clipboard'
import { openExternal } from '@/utils/openExternal'

// #header hides the view switcher, so m/w/d would leave Month with no way back.
const calendarConfig = { defaultMode: 'Month', enableShortcuts: false }

const router = useRouter()

const breadcrumbs = computed(() => [
	{ label: __('Calendar'), route: { name: 'Calendar' } },
])

const events = createResource({
	url: 'lms.lms.learner_calendar.get_my_calendar',
	cache: ['learnerCalendar'],
	auto: true,
	transform: (data) =>
		data.map((event) => ({
			...event,
			color: event.type === 'quiz' ? 'amber' : 'blue',
			venue: event.batch,
		})),
})

// Cached rows still beat an error, so only an empty failed load shows one.
const loadError = computed(() => Boolean(events.error) && !events.data?.length)

const feedUrl = createResource({
	url: 'lms.lms.learner_calendar.get_calendar_feed_url',
})

const copyFeedUrl = async () => {
	const url = await feedUrl.fetch()
	try {
		await copyText(url)
		toast.success(
			__('Calendar link copied. Add it to your calendar app by URL.')
		)
	} catch {
		toast.error(__('Could not copy the link: {0}').format(url))
	}
}

const openEvent = (event) => {
	if (event.type === 'quiz') {
		router.push({ name: 'QuizPage', params: { quizID: event.name } })
	} else if (event.url) {
		openExternal(event.url)
	} else {
		router.push({ name: 'BatchDetail', params: { batchName: event.batch } })
	}
}
</script>
