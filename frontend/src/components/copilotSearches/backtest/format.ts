/** Thousands-separated integer, tolerant of null/undefined counts from the API. */
export function fmt(n: number): string {
	return (n ?? 0).toLocaleString()
}

/**
 * Bar width as a percentage of the row's largest value. Floored at 3% so a value
 * of 1 next to a peak of 500 still leaves a visible stub rather than nothing.
 */
export function pct(n: number, max: number): string {
	return `${Math.max(3, Math.round((n / Math.max(1, max)) * 100))}%`
}
