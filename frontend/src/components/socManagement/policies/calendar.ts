// Business-hours calendars (#1187): pure helpers behind the calendar editor.
//
// A calendar is working windows per weekday, in a timezone, minus holidays. Targets of a
// policy cell set to "business hours" count only that time — the backend does the
// arithmetic (`domain/calendar.py`); these helpers only shape, validate and summarise
// what the editor holds, so the editor can refuse what the backend would.
import type { BusinessCalendar, CalendarPayload, Weekday, WorkingWindow } from "@/types/soc-management"

export const WEEKDAYS: Weekday[] = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

export const WEEKDAY_LABEL: Record<Weekday, string> = {
	mon: "Monday",
	tue: "Tuesday",
	wed: "Wednesday",
	thu: "Thursday",
	fri: "Friday",
	sat: "Saturday",
	sun: "Sunday"
}

/** The window a day gets when it is switched open. */
export const DEFAULT_WINDOW: WorkingWindow = ["09:00", "17:00"]

/** 570 → `"09:30"`. */
export function fromMinutes(total: number): string {
	const clamped = Math.max(0, Math.min(total, 23 * 60 + 59))
	return `${String(Math.floor(clamped / 60)).padStart(2, "0")}:${String(clamped % 60).padStart(2, "0")}`
}

/** The window "add" appends: an hour after the day's last one, so the analyst adjusts rather than types. */
export function nextWindow(windows: WorkingWindow[]): WorkingWindow {
	const last = windows.at(-1)
	const start = (last && toMinutes(last[1])) ?? toMinutes(DEFAULT_WINDOW[0]) ?? 540
	return [fromMinutes(start), fromMinutes(start + 60)]
}

export interface EditableCalendar {
	timezone: string
	week: Record<Weekday, WorkingWindow[]>
	holidays: string[]
}

const TIME = /^(?:[01]\d|2[0-3]):[0-5]\d$/

/** `"09:30"` → 570. `null` when not a valid HH:MM. */
export function toMinutes(value: string): number | null {
	if (!TIME.test(value)) return null
	const [hours, minutes] = value.split(":").map(Number)
	return hours * 60 + minutes
}

/** A deep copy the editor may mutate freely; days the source omits are closed. */
export function toEditableCalendar(
	calendar: Pick<BusinessCalendar, "timezone" | "holidays"> & {
		week: Partial<Record<Weekday, WorkingWindow[]>>
	}
): EditableCalendar {
	return {
		timezone: calendar.timezone,
		week: Object.fromEntries(
			WEEKDAYS.map(day => [day, (calendar.week[day] ?? []).map(([start, end]) => [start, end] as WorkingWindow)])
		) as Record<Weekday, WorkingWindow[]>,
		holidays: [...calendar.holidays].sort()
	}
}

export function buildCalendarPayload(
	calendar: EditableCalendar,
	customerCode: string | null,
	applyToOpen: boolean
): CalendarPayload {
	return {
		customer_code: customerCode,
		timezone: calendar.timezone,
		week: Object.fromEntries(
			WEEKDAYS.filter(day => calendar.week[day].length).map(day => [day, sortWindows(calendar.week[day])])
		),
		holidays: [...new Set(calendar.holidays)].sort(),
		apply_to_open: applyToOpen
	}
}

export function isCalendarDirty(calendar: EditableCalendar, original: EditableCalendar): boolean {
	return JSON.stringify(normalise(calendar)) !== JSON.stringify(normalise(original))
}

function normalise(calendar: EditableCalendar) {
	return { ...buildCalendarPayload(calendar, null, false), apply_to_open: undefined }
}

function sortWindows(windows: WorkingWindow[]): WorkingWindow[] {
	return [...windows].sort((a, b) => (toMinutes(a[0]) ?? 0) - (toMinutes(b[0]) ?? 0))
}

/** What is wrong with one day's windows, phrased for the editor; `null` when fine. */
export function dayError(windows: WorkingWindow[]): string | null {
	const parsed = windows.map(([start, end]) => [toMinutes(start), toMinutes(end)] as const)
	if (parsed.some(([start, end]) => start == null || end == null)) return "Times are HH:MM"
	if (parsed.some(([start, end]) => (start as number) >= (end as number))) return "A window must start before it ends"
	const ordered = [...parsed].sort((a, b) => (a[0] as number) - (b[0] as number))
	for (let i = 1; i < ordered.length; i++) {
		if ((ordered[i][0] as number) < (ordered[i - 1][1] as number)) return "Windows overlap"
	}
	return null
}

/** The first problem anywhere in the calendar, or `null`. */
export function calendarError(calendar: EditableCalendar): string | null {
	if (!calendar.timezone) return "Pick a timezone"
	for (const day of WEEKDAYS) {
		const error = dayError(calendar.week[day])
		if (error) return `${WEEKDAY_LABEL[day]}: ${error.toLowerCase()}`
	}
	if (!WEEKDAYS.some(day => calendar.week[day].length)) return "Open at least one day"
	return null
}

/** Working minutes in a week, ignoring holidays. */
export function weeklyMinutes(calendar: EditableCalendar): number {
	return WEEKDAYS.reduce(
		(total, day) =>
			total +
			calendar.week[day].reduce((sum, [start, end]) => {
				const from = toMinutes(start)
				const to = toMinutes(end)
				return from != null && to != null && to > from ? sum + to - from : sum
			}, 0),
		0
	)
}

/** A window as a slice of the day, for the 24-hour strip: `{ left: 37.5, width: 33.3 }` (percent). */
export function windowSpan([start, end]: WorkingWindow): { left: number; width: number } | null {
	const from = toMinutes(start)
	const to = toMinutes(end)
	if (from == null || to == null || to <= from) return null
	return { left: (from / 1440) * 100, width: ((to - from) / 1440) * 100 }
}

/** Every IANA zone the browser knows, falling back to a short list on old engines. */
export function timezoneOptions(current?: string): { label: string; value: string }[] {
	let zones: string[]
	try {
		zones = Intl.supportedValuesOf("timeZone")
	} catch {
		zones = ["UTC", "Europe/London", "Europe/Rome", "America/New_York", "America/Los_Angeles", "Asia/Tokyo"]
	}
	if (!zones.includes("UTC")) zones = ["UTC", ...zones]
	if (current && !zones.includes(current)) zones = [current, ...zones]
	return zones.map(zone => ({ label: zone.replace(/_/g, " "), value: zone }))
}

/** The browser's own zone, a sensible first pick for a new calendar. */
export function localTimezone(): string {
	return new Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"
}
