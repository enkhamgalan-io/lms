<template>
	<ChartCard v-bind="$attrs" data-testid="course-views">
		<div class="flex h-full flex-col gap-3">
			<div class="flex items-center justify-between gap-2">
				<div>
					<div class="text-p-base-medium text-ink-gray-8">
						{{ __('Lesson views') }}
					</div>
					<div class="text-p-sm text-ink-gray-6">
						{{
							period === 'day'
								? __('Per day, last 30 days')
								: __('Per month, last 12 months')
						}}
					</div>
				</div>
				<TabButtons v-model="period" :buttons="periods" />
			</div>
			<div v-if="views.data && !hasViews" class="text-p-sm text-ink-gray-6">
				{{ __('No lesson has been opened in this time.') }}
			</div>
			<template v-else>
				<AreaChart
					class="min-h-40 flex-1"
					:data="views.data?.series ?? []"
					x="period"
					:y="SERIES"
					:loading="!views.data"
					:x-axis="{
						type: 'time',
						timeGrain: period === 'day' ? 'day' : 'month',
					}"
					:y-axis="{ echartOptions: { minInterval: 1 } }"
					:series-config="seriesConfig"
				>
					<template #loading>
						<PanelSkeleton />
					</template>
				</AreaChart>
				<ol
					v-if="views.data?.lessons.length"
					class="space-y-1 text-p-sm"
					data-testid="most-viewed"
				>
					<li
						v-for="row in views.data.lessons"
						:key="row.lesson"
						class="flex items-baseline justify-between gap-3 text-ink-gray-7"
					>
						<span class="truncate">{{ row.title }}</span>
						<span class="shrink-0 tabular-nums text-ink-gray-6">
							{{
								__('{0} views · {1} learners').format(row.views, row.viewers)
							}}
						</span>
					</li>
				</ol>
			</template>
		</div>
	</ChartCard>
</template>

<script setup lang="ts">
import { TabButtons, createResource } from 'frappe-ui'
import { AreaChart, ChartCard } from 'frappe-ui/charts'
import type { SeriesStyle } from 'frappe-ui/charts'
import { computed, ref, watch } from 'vue'
import PanelSkeleton from '@/components/Dashboard/PanelSkeleton.vue'

/**
 * How often the course's lessons were opened, per day or month, and the most
 * opened lessons over the same span. dashboard.course.get_course_views sums
 * the LMS Lesson View rows; the course's staff alone may read them.
 */

type Series = 'views' | 'viewers'

defineOptions({ inheritAttrs: false })

const props = defineProps<{ courseName: string }>()

const SERIES: Series[] = ['views', 'viewers']

const period = ref<'day' | 'month'>('day')

const periods = computed(() => [
	{ label: __('Days'), value: 'day' },
	{ label: __('Months'), value: 'month' },
])

const views = createResource<{
	series: { period: string; views: number; viewers: number }[]
	lessons: { lesson: string; title: string; views: number; viewers: number }[]
}>({
	url: 'lms.lms.dashboard.course.get_course_views',
	makeParams: () => ({ course: props.courseName, period: period.value }),
	auto: true,
})

watch(period, () => views.reload())

const hasViews = computed(() =>
	(views.data?.series ?? []).some((row) => row.views)
)

const seriesConfig = computed<Record<Series, SeriesStyle>>(() => ({
	views: { label: __('Views') },
	viewers: { label: __('Learners') },
}))
</script>
