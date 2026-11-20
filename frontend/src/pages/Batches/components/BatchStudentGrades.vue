<template>
	<section
		data-section="grades"
		class="flex flex-col gap-[10px] py-3"
		:aria-label="__('Grades')"
	>
		<div class="flex items-baseline justify-between gap-2">
			<h3 class="text-[14px] font-semibold text-ink-gray-8">
				{{ __('Grades') }}
			</h3>
			<span class="text-[12px] text-ink-gray-6" data-testid="final-score">
				{{ __('Final score: {0}').format(String(grades.final_score)) }}
			</span>
		</div>
		<div class="grid grid-cols-2 gap-3">
			<FormControl
				v-for="field in FIELDS"
				:key="field.name"
				v-model="draft[field.name]"
				type="number"
				:label="field.label()"
				variant="outline"
			/>
		</div>
		<div class="flex justify-end">
			<Button
				variant="subtle"
				:loading="save.loading"
				:disabled="!dirty"
				@click="submit"
			>
				{{ __('Save grades') }}
			</Button>
		</div>
	</section>
</template>
<script setup lang="ts">
import { Button, FormControl, createResource, toast } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import type { StudentGrades } from '@/types'
import { resourceErrorMessage } from '@/utils/resource'

type GradeField = Exclude<keyof StudentGrades, 'final_score'>

const FIELDS: { name: GradeField; label: () => string }[] = [
	{ name: 'exam_score', label: () => __('Exam') },
	{ name: 'attendance_score', label: () => __('Attendance') },
	{ name: 'progress_score', label: () => __('Progress') },
	{ name: 'bonus_score', label: () => __('Bonus') },
]

const props = defineProps<{
	batchName: string
	enrollment: string
	grades: StudentGrades
}>()

const emit = defineEmits<{ saved: [] }>()

const draft = ref<Record<GradeField, number>>({} as Record<GradeField, number>)
watch(
	() => props.grades,
	(grades) => {
		for (const { name } of FIELDS) draft.value[name] = grades[name]
	},
	{ immediate: true }
)

const dirty = computed(() =>
	FIELDS.some(({ name }) => Number(draft.value[name]) !== props.grades[name])
)

const save = createResource({
	url: 'lms.lms.dashboard.batch.set_student_grades',
})

const submit = (): void => {
	save
		.submit({
			batch: props.batchName,
			enrollment: props.enrollment,
			grades: draft.value,
		})
		.then(() => {
			toast.success(__('Grades saved'))
			emit('saved')
		})
		.catch((error: unknown) =>
			toast.error(resourceErrorMessage(error, __('Could not save grades')))
		)
}
</script>
