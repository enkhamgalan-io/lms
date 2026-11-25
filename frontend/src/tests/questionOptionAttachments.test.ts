import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { reactive } from 'vue'
import QuestionAnswers from '@/components/Quiz/QuestionAnswers.vue'
import { blankOptionFields, fileName, isImageFile } from '@/utils/quizQuestion'

const GATED =
	'/api/method/lms.lms.doctype.lms_question.lms_question.serve_question_resource?file_url='

describe('option attachments', () => {
	it('tells an image from another file, also behind the gated endpoint', () => {
		expect(isImageFile(GATED + '%2Fprivate%2Ffiles%2Fshape.PNG')).toBe(true)
		expect(isImageFile('/private/files/law.pdf')).toBe(false)
		expect(isImageFile(null)).toBe(false)
		expect(
			fileName(
				GATED + '%2Fprivate%2Ffiles%2F%D1%85%D1%83%D1%83%D0%BB%D1%8C.pdf',
			),
		).toBe('хууль.pdf')
	})

	it('moves a file up with its option when an earlier option is removed', async () => {
		const question = reactive({
			...blankOptionFields(),
			option_1: 'Square',
			option_2: 'Circle',
			option_3: 'Triangle',
			option_3_attachment: '/private/files/triangle.png',
		})
		const wrapper = mount(QuestionAnswers, {
			props: { uiType: 'single', question },
			global: { mocks: { __: (globalThis as any).__ } },
		})
		await wrapper.find('button[aria-label="Remove option 1"]').trigger('click')
		expect(question.option_2).toBe('Triangle')
		expect(question.option_2_attachment).toBe('/private/files/triangle.png')
		expect(question.option_3_attachment).toBeNull()
	})
})
