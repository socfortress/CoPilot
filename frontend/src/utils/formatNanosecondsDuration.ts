export function formatNanosecondsDuration(nanoseconds?: number | null): string {
	if (nanoseconds == null || !Number.isFinite(nanoseconds) || nanoseconds < 0) {
		return "N/A"
	}

	const milliseconds = nanoseconds / 1_000_000

	if (milliseconds < 1000) {
		return `${Math.round(milliseconds)} ms`
	}

	const totalSeconds = milliseconds / 1000

	if (totalSeconds < 60) {
		return `${Number(totalSeconds.toFixed(2))} s`
	}

	const minutes = Math.floor(totalSeconds / 60)
	const seconds = Math.round(totalSeconds % 60)

	if (minutes < 60) {
		return seconds > 0 ? `${minutes} min ${seconds} s` : `${minutes} min`
	}

	const hours = Math.floor(minutes / 60)
	const remainingMinutes = minutes % 60

	return remainingMinutes > 0 ? `${hours} h ${remainingMinutes} min` : `${hours} h`
}
