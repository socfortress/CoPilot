import type { NotificationPreference } from "@/types/notifications"
import { describe, expect, it } from "vitest"
import { digestLabel, emailUnavailableText, EVENT_COPY, samePreferences } from "../notificationPreferences"

const PREFS: NotificationPreference[] = [
	{ event: "alert_created", in_app: true, email: "off", min_severity: "High" },
	{ event: "case_closed", in_app: true, email: "digest", min_severity: null }
]

describe("notification preferences helpers (#1282)", () => {
	it("compares choices event by event, whatever the order", () => {
		expect(samePreferences(PREFS, [...PREFS].reverse())).toBe(true)
		expect(samePreferences(PREFS, [PREFS[0]!, { ...PREFS[1]!, email: "immediate" }])).toBe(false)
		expect(samePreferences(PREFS, [{ ...PREFS[0]!, min_severity: "Low" }, PREFS[1]!])).toBe(false)
		expect(samePreferences(PREFS, [PREFS[0]!])).toBe(false)
	})

	it("names the summary's hour, in UTC", () => {
		expect(digestLabel(7)).toBe("Daily summary (07:00 UTC)")
		expect(digestLabel(18)).toBe("Daily summary (18:00 UTC)")
	})

	it("explains why email cannot be chosen, in the user's words", () => {
		const base = { enabled: true, digest_hour_utc: 7 }
		expect(emailUnavailableText(null)).toBeNull()
		expect(emailUnavailableText({ ...base, email_available: true, email_unavailable_reason: null })).toBeNull()
		expect(
			emailUnavailableText({
				...base,
				email_available: false,
				email_unavailable_reason: "The user has no email address"
			})
		).toContain("no email address")
		expect(
			emailUnavailableText({ ...base, email_available: false, email_unavailable_reason: "SMTP is not configured" })
		).toContain("not set up")
	})

	it("describes every event, with a bundled icon", () => {
		for (const copy of Object.values(EVENT_COPY)) {
			expect(copy.label).toBeTruthy()
			expect(copy.icon).toMatch(/^carbon:/)
		}
	})
})
