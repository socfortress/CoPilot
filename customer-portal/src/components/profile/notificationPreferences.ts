import type { NotificationAvailability, NotificationEventName, NotificationPreference } from "@/types/notifications"

/** What each event is called in the profile, and when it fires (#1282). */
export const EVENT_COPY: Record<NotificationEventName, { label: string; description: string; icon: string }> = {
	alert_created: {
		label: "New alerts",
		description: "A new alert of your organization, from the severity you choose.",
		icon: "carbon:warning-alt"
	},
	waiting_on_you: {
		label: "Waiting on you",
		description: "The SOC needs your reply on an alert or a case.",
		icon: "carbon:user-follow"
	},
	case_closed: {
		label: "Closed cases",
		description: "A case of your organization was closed.",
		icon: "carbon:checkmark-outline"
	},
	report_ready: {
		label: "Reports ready",
		description: "A report you generated, or one the SOC shared with you, is ready.",
		icon: "carbon:document"
	}
}

/** The digest's option, with its hour: the time is in UTC, and says so. */
export function digestLabel(hourUtc: number): string {
	return `Daily summary (${String(hourUtc).padStart(2, "0")}:00 UTC)`
}

/** Why email cannot be chosen, in the user's words, or null when it can. */
export function emailUnavailableText(availability: NotificationAvailability | null): string | null {
	if (!availability || availability.email_available) return null
	if (availability.email_unavailable_reason === "The user has no email address") {
		return "Your account has no email address, so notifications reach the portal only. Ask your SOC to add one."
	}
	return "Email notifications are not set up on this portal yet, so notifications reach the portal only."
}

/** Whether two sets of choices are the same, event by event. */
export function samePreferences(a: NotificationPreference[], b: NotificationPreference[]): boolean {
	if (a.length !== b.length) return false
	const byEvent = new Map(b.map(pref => [pref.event, pref]))
	return a.every(pref => {
		const other = byEvent.get(pref.event)
		return (
			!!other &&
			other.in_app === pref.in_app &&
			other.email === pref.email &&
			(other.min_severity ?? null) === (pref.min_severity ?? null)
		)
	})
}
