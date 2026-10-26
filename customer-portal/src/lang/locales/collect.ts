/** One language's messages from its files, keyed by file name (`./alerts.json` → `alerts`). */
export function collectMessages(files: Record<string, unknown>): Record<string, unknown> {
	return Object.fromEntries(
		Object.entries(files).map(([path, messages]) => [path.replace(/^.*\/|\.json$/g, ""), messages])
	)
}
