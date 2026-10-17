/**
 * Pure helpers for downloading a report (#1263): the "Report ready" notification sends the
 * user to the Reports page with `?download=<id>`, which may land before the list is loaded,
 * so the file name can come from the response itself.
 */

/** The report id a `?download=` query names, or null when it names none. */
export function downloadQueryId(value: unknown): number | null {
	const raw = Array.isArray(value) ? value[0] : value
	if (typeof raw !== "string" || !/^\d+$/.test(raw)) return null
	const id = Number(raw)
	return id > 0 && Number.isSafeInteger(id) ? id : null
}

/** The file name a `Content-Disposition` header carries, quoted or not (RFC 6266, `filename*` first). */
export function fileNameFromDisposition(header: string | null | undefined): string | null {
	if (!header) return null
	const extended = /filename\*\s*=\s*(?:UTF-8|utf-8)''([^;]+)/.exec(header)
	if (extended?.[1]) {
		try {
			return decodeURIComponent(extended[1].trim().replace(/^"|"$/g, ""))
		} catch {
			// A malformed escape: fall back to the plain parameter.
		}
	}
	const plain = /filename\s*=\s*("([^"]*)"|[^;]+)/.exec(header)
	const name = (plain?.[2] ?? plain?.[1] ?? "").trim()
	return name || null
}
