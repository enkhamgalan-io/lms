// Office and text files a lesson offers for download: there is no viewer for them.
// UploadPlugin accepts them; the Upload block draws each as a download card.
export const DOCUMENT_EXTENSIONS = [
	'doc',
	'docx',
	'xls',
	'xlsx',
	'ppt',
	'pptx',
	'odt',
	'ods',
	'odp',
	'csv',
	'txt',
]

// The File doctype's file_type: the extension in upper case.
export const DOCUMENT_TYPES = new Set(
	DOCUMENT_EXTENSIONS.map((extension) => extension.toUpperCase())
)
