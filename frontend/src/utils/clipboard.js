// navigator.clipboard exists only on HTTPS or localhost, so a site served over
// plain http (a bench on a LAN hostname) falls back to the older copy command.
export const copyText = async (text) => {
	if (navigator.clipboard?.writeText) {
		await navigator.clipboard.writeText(text)
		return
	}
	const field = document.createElement('textarea')
	field.value = text
	field.setAttribute('readonly', '')
	field.style.position = 'fixed'
	field.style.opacity = '0'
	document.body.appendChild(field)
	field.select()
	const copied = document.execCommand('copy')
	field.remove()
	if (!copied) throw new Error('copy failed')
}
