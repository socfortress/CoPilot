import { i18nGlobal } from "@/lang"
import dayjs from "@/utils/dayjs"

/**
 * How long something has been running: a report generating (#1263), an AI analysis
 * (#1273). The backend's times are naive UTC (`2026-10-16T09:00:00`, no offset): they
 * are read as UTC, never as the viewer's local time.
 */

/** Seconds from a stored (UTC) time to `now`, never negative; null when the time is unreadable. */
export function secondsSince(storedUtc: string, now: number): number | null {
	const started = dayjs.utc(storedUtc)
	if (!started.isValid()) return null
	return Math.max(0, Math.floor((now - started.valueOf()) / 1000))
}

/** "<1 min", "4 min", "1 h 05 min": short enough for a tag. */
export function elapsedLabel(seconds: number): string {
	const minutes = Math.floor(seconds / 60)
	if (minutes < 1) return i18nGlobal.t("common.elapsed.underMinute")
	if (minutes < 60) return i18nGlobal.t("common.elapsed.minutes", { minutes })
	return i18nGlobal.t("common.elapsed.hours", {
		hours: Math.floor(minutes / 60),
		minutes: String(minutes % 60).padStart(2, "0")
	})
}
