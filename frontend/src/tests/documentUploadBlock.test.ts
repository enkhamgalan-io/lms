import { describe, expect, it, vi } from 'vitest'
import { Upload } from '@/utils/upload'

vi.hoisted(() => {
	window.matchMedia ??= (() => ({
		matches: false,
		addEventListener: () => {},
		removeEventListener: () => {},
	})) as unknown as typeof window.matchMedia
})
vi.mock('@/utils/pdfViewer', () => ({ usesWebkitPdfViewer: () => false }))
vi.mock('@/stores/settings', () => ({
	useSettings: () => ({ settings: { data: {} } }),
}))
vi.mock('@/stores/user', () => ({ usersStore: () => ({ userResource: {} }) }))
vi.mock('@/stores/session', () => ({ sessionStore: () => ({ user: null }) }))
vi.stubGlobal(
	'fetch',
	vi.fn(async () => new Response('{"message": {}}'))
)
vi.stubGlobal('__', (text: string) => text)

const render = (file_url: string, file_type: string) =>
	new Upload({ data: { file_url, file_type }, readOnly: true }).render()

describe('a document in a lesson', () => {
	it.each(['DOCX', 'xlsx', 'PPTX', 'CSV'])(
		'offers a %s file for download, not as an image',
		(fileType) => {
			const block = render(
				`/private/files/Rules%202026.${fileType.toLowerCase()}`,
				fileType
			)
			const link = block.querySelector<HTMLAnchorElement>(
				'[data-testid="file-download"]'
			)
			expect(link).not.toBeNull()
			expect(link!.getAttribute('href')).toBe(
				`/private/files/Rules%202026.${fileType.toLowerCase()}`
			)
			expect(link!.textContent).toContain(
				`Rules 2026.${fileType.toLowerCase()}`
			)
			expect(block.querySelector('img')).toBeNull()
		}
	)

	it('draws nothing for a link that is not a file', () => {
		const block = render('javascript:alert(1)', 'DOCX')
		expect(block.querySelector('a')).toBeNull()
	})

	it('still draws an image as an image', () => {
		const block = render('/files/map.png', 'PNG')
		expect(block.querySelector('img')).not.toBeNull()
		expect(block.querySelector('[data-testid="file-download"]')).toBeNull()
	})
})
