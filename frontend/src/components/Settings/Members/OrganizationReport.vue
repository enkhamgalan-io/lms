<template>
	<SettingsLayout
		:title="__(label)"
		:description="__('Course progress of the people in your organizations.')"
	>
		<template #header-actions>
			<Button
				:label="__('Export CSV')"
				:disabled="!rows.length"
				@click="exportCsv"
			>
				<template #prefix>
					<span class="lucide-download size-4" aria-hidden="true" />
				</template>
			</Button>
		</template>

		<div class="flex flex-wrap items-end gap-3">
			<Link
				v-model="organization"
				class="w-60"
				doctype="LMS Organization"
				:label="__('Organization')"
				:placeholder="__('All my organizations')"
			/>
			<Select
				v-model="course"
				class="w-60"
				:label="__('Course')"
				:options="courseOptions"
			/>
		</div>

		<div class="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
			<div
				v-for="stat in stats"
				:key="stat.label"
				class="rounded-[10px] bg-surface-gray-1 px-4 py-3"
			>
				<div class="text-p-sm text-ink-gray-6">{{ stat.label }}</div>
				<div class="text-p-xl-semibold tabular-nums text-ink-gray-9">
					{{ stat.value }}
				</div>
			</div>
		</div>

		<div v-if="report.loading && !report.data" class="py-10 text-center">
			<LoadingIndicator class="mx-auto size-5 text-ink-gray-5" />
		</div>
		<div
			v-else-if="!rows.length"
			class="py-10 text-center text-p-base text-ink-gray-6"
		>
			{{ __('No enrollments yet.') }}
		</div>
		<div v-else class="mt-4 overflow-x-auto">
			<table class="w-full text-p-sm" data-testid="organization-report">
				<thead class="text-ink-gray-6">
					<tr class="border-b border-outline-gray-2">
						<th
							v-for="column in columns"
							:key="column"
							class="py-2 pe-3 text-start font-normal"
						>
							{{ column }}
						</th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="row in rows"
						:key="row.member + row.course"
						class="border-b border-outline-gray-1 text-ink-gray-8"
					>
						<td class="py-2 pe-3">
							<div>{{ row.full_name }}</div>
							<div class="text-ink-gray-5">
								{{ [row.designation, row.rank].filter(Boolean).join(' · ') }}
							</div>
						</td>
						<td class="py-2 pe-3">{{ row.organization }}</td>
						<td class="py-2 pe-3">{{ row.course_title }}</td>
						<td class="py-2 pe-3 tabular-nums">{{ row.progress }}%</td>
						<td class="py-2 pe-3 tabular-nums">
							{{ row.quiz_average === null ? '—' : `${row.quiz_average}%` }}
						</td>
						<td class="py-2 pe-3">
							<Badge
								v-if="row.certificate"
								:label="__('Issued')"
								theme="green"
							/>
							<span v-else class="text-ink-gray-5">—</span>
						</td>
						<td class="py-2 pe-3">
							<span :class="row.access_expired ? 'text-ink-red-6' : ''">
								{{ row.valid_until || __('No end') }}
							</span>
						</td>
					</tr>
				</tbody>
			</table>
		</div>
	</SettingsLayout>
</template>

<script setup lang="ts">
import { Badge, Button, LoadingIndicator, createResource } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import Link from '@/components/Controls/Link.vue'
import Select from '@/components/Controls/Select.vue'
import SettingsLayout from '@/components/Layouts/settings/desktop/SettingsLayout.vue'

/**
 * Settings > Organization Report: one row per course enrollment of the people
 * the viewer manages. get_organization_report scopes it on the server; an
 * Organization Manager's picker only offers their own organizations.
 */

type ReportRow = {
	member: string
	full_name: string
	organization: string
	designation: string | null
	rank: string | null
	course: string
	course_title: string
	progress: number
	quiz_average: number | null
	certificate: string | null
	valid_until: string | null
	access_expired: boolean
}

defineProps<{ label: string }>()

const organization = ref('')
const course = ref('')

const report = createResource<{
	rows: ReportRow[]
	courses: { value: string; label: string }[]
}>({
	url: 'lms.lms.api.get_organization_report',
	makeParams: () => ({
		organization: organization.value || null,
		course: course.value || null,
	}),
	auto: true,
})

// The course list comes back with the rows, so a narrower organization
// narrows it too; a course that is no longer offered is let go.
watch(organization, () => {
	course.value = ''
	report.reload()
})
watch(course, () => report.reload())

const rows = computed(() => report.data?.rows ?? [])

const courseOptions = computed(() => [
	{ label: __('All courses'), value: '' },
	...(report.data?.courses ?? []),
])

const stats = computed(() => {
	const all = rows.value
	return [
		{ label: __('People'), value: new Set(all.map((row) => row.member)).size },
		{ label: __('Enrollments'), value: all.length },
		{
			label: __('Completed'),
			value: all.filter((row) => row.progress >= 100).length,
		},
		{
			label: __('Certified'),
			value: all.filter((row) => row.certificate).length,
		},
	]
})

const columns = computed(() => [
	__('Person'),
	__('Organization'),
	__('Course'),
	__('Progress'),
	__('Quiz average'),
	__('Certificate'),
	__('Access until'),
])

const csvCell = (value: unknown) => {
	const text = value === null || value === undefined ? '' : String(value)
	return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

const exportCsv = () => {
	const header = [
		__('Name'),
		__('Email'),
		__('Organization'),
		__('Designation'),
		__('Rank'),
		__('Course'),
		__('Progress'),
		__('Quiz average'),
		__('Certificate'),
		__('Access until'),
	]
	const lines = rows.value.map((row) =>
		[
			row.full_name,
			row.member,
			row.organization,
			row.designation,
			row.rank,
			row.course_title,
			row.progress,
			row.quiz_average,
			row.certificate,
			row.valid_until,
		]
			.map(csvCell)
			.join(',')
	)
	// A byte order mark, so spreadsheet apps read Cyrillic names as UTF-8.
	const blob = new Blob(['﻿' + [header.join(','), ...lines].join('\n')], {
		type: 'text/csv;charset=utf-8',
	})
	const link = document.createElement('a')
	link.href = URL.createObjectURL(blob)
	link.download = 'organization-report.csv'
	link.click()
	URL.revokeObjectURL(link.href)
}
</script>
