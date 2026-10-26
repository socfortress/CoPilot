import type {
	NotificationAvailability,
	NotificationEventName,
	NotificationPreference,
	NotificationSeverity
} from "@/types/notifications"
import { i18nGlobal } from "@/lang"

/** What each event is called in the profile, and when it fires (#1282), in the user's language (#1310). */
export const EVENT_COPY: Record<NotificationEventName, { readonly label: string; readonly description: string; icon: string }> = {
	alert_created: {
		get label() {
			return i18nGlobal.t("profile.notifications.events.alertCreated.label")
		},
		get description() {
			return i18nGlobal.t("profile.notifications.events.alertCreated.description")
		},
		icon: "carbon:warning-alt"
	},
	waiting_on_you: {
		get label() {
			return i18nGlobal.t("profile.notifications.events.waitingOnYou.label")
		},
		get description() {
			return i18nGlobal.t("profile.notifications.events.waitingOnYou.description")
		},
		icon: "carbon:user-follow"
	},
	case_closed: {
		get label() {
			return i18nGlobal.t("profile.notifications.events.caseClosed.label")
		},
		get description() {
			return i18nGlobal.t("profile.notifications.events.caseClosed.description")
		},
		icon: "carbon:checkmark-outline"
	},
	report_ready: {
		get label() {
			return i18nGlobal.t("profile.notifications.events.reportReady.label")
		},
		get description() {
			return i18nGlobal.t("profile.notifications.events.reportReady.description")
		},
		icon: "carbon:document"
	}
}

/** A severity's name as the profile shows it ("Critical"); the value sent to the API stays as it is. */
export function severityLabel(severity: NotificationSeverity): string {
	const key = severity.toLowerCase() as Lowercase<NotificationSeverity>
	return i18nGlobal.t(`profile.notifications.severities.${key}`)
}

/** The digest's option, with its hour: the time is in UTC, and says so. */
export function digestLabel(hourUtc: number): string {
	return i18nGlobal.t("profile.notifications.digest", { hour: String(hourUtc).padStart(2, "0") })
}

/** Why email cannot be chosen, in the user's words, or null when it can. */
export function emailUnavailableText(availability: NotificationAvailability | null): string | null {
	if (!availability || availability.email_available) return null
	// The API's reason is matched, never shown: it is in English.
	if (availability.email_unavailable_reason === "The user has no email address") {
		return i18nGlobal.t("profile.notifications.noEmailAddress")
	}
	return i18nGlobal.t("profile.notifications.emailNotSetUp")
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
