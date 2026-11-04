import { createPinia, setActivePinia } from "pinia"
import { describe, expect, it } from "vitest"
import i18n from "@/lang"
import { SUPPORTED_LOCALES } from "@/lang/config"
import * as locales from "@/lang/locales"
import dayjs from "@/utils/dayjs"
import { checkedLine, ERROR_CODES, errorCodeOf, errorText, knownCode, threadMatches, threadTime } from "../talonChat"

/** The talon-analyst SPEC §8 error table's codes the portal can meet (the `ioc_*` ones are tool results). */
const SPEC_CODES = [
	"invalid_request",
	"invalid_headers",
	"not_portal_role",
	"portal_role_refused",
	"customer_not_accessible",
	"portal_off",
	"settings_unavailable",
	"thread_not_found",
	"thread_archived",
	"access_removed",
	"thread_limit",
	"new_thread_limit",
	"alert_not_found",
	"body_too_large",
	"message_too_long",
	"busy_thread",
	"busy_user",
	"busy",
	"turn_limit",
	"timeout",
	"budget_customer",
	"budget_portal",
	"budget_portal_user",
	"messages_customer",
	"messages_user",
	"budget_unavailable",
	"failed",
	"draft_not_found",
	"draft_expired",
	"draft_conflict",
	"read_only",
	"soc_requests_off",
	"soc_request_limit",
	"soc_request_cooldown",
	"invalid_question",
	"not_found",
	"internal_failure"
]

describe("ask Talon's error wording", () => {
	it("words every code of the contract's table", () => {
		expect(SPEC_CODES.filter(code => !(ERROR_CODES as readonly string[]).includes(code))).toEqual([])
	})

	it("has a text for every code in every language", () => {
		for (const locale of SUPPORTED_LOCALES) {
			const errors = (locales[locale] as unknown as { talonChat: { errors: Record<string, string> } }).talonChat.errors
			expect(ERROR_CODES.filter(code => !errors[code]?.trim()), locale).toEqual([])
		}
	})

	it("localizes by code, in the user's language", () => {
		expect(errorText("portal_off")).toBe("Ask Talon is turned off for this organization.")
		i18n.global.locale.value = "de"
		expect(errorText("portal_off")).toBe("Talon fragen ist für diese Organisation ausgeschaltet.")
		expect(errorText("soc_request_cooldown")).toContain("in ein paar Minuten")
	})

	it("never shows a code it doesn't know, nor the server's text", () => {
		expect(knownCode("something_new")).toBe("unknown")
		expect(knownCode(null)).toBe("unknown")
		expect(errorText("portal chat is turned off for this customer")).toBe("Something went wrong. Try again.")
	})

	it("reads the code of a refused request, or says no answer came", () => {
		expect(errorCodeOf({ response: { status: 409, data: { detail: "x", code: "thread_limit" } } })).toBe("thread_limit")
		expect(errorCodeOf({ response: { status: 422, data: { detail: [{ msg: "x" }] } } })).toBeNull()
		expect(errorCodeOf({ message: "Network Error" })).toBe("network")
	})
})

describe("the checked line", () => {
	const items = [
		{ kind: "alert", count: 1 },
		{ kind: "event_search", count: 2 },
		{ kind: "intel", type: "ip", count: 1 }
	]

	it("reads as the contract's sample, in English", () => {
		expect(checkedLine(items)).toBe("Checked: the alert, 2 event searches, 1 IP address")
	})

	it("follows the user's language, plurals included", () => {
		i18n.global.locale.value = "cs"
		expect(checkedLine([{ kind: "event", count: 3 }, { kind: "event_search", count: 5 }, { kind: "intel", type: "domain", count: 7 }])).toBe(
			"Zkontrolováno: 3 události, 5 vyhledávání událostí, 7 domén"
		)
		i18n.global.locale.value = "fr"
		expect(checkedLine(items)).toBe("Vérifié : l'alerte, 2 recherches d'événements, 1 adresse IP")
	})

	it("leaves out a kind it doesn't know, and words an unknown intel type generally", () => {
		expect(checkedLine([{ kind: "portal_get_alert", count: 1 }])).toBeNull()
		expect(checkedLine([{ kind: "intel", type: "weird", count: 2 }, { kind: "made_up", count: 1 }])).toBe(
			"Checked: 2 threat-intel lookups"
		)
		expect(checkedLine(null)).toBeNull()
	})
})

describe("the inbox's row time", () => {
	// A Wednesday afternoon, local time.
	const now = dayjs("2026-10-28T15:00:00")

	it("is the time today, the weekday within the week, else the date", () => {
		setActivePinia(createPinia())
		expect(threadTime(dayjs("2026-10-28T09:05:00").toISOString(), now)).toBe("09:05")
		expect(threadTime(dayjs("2026-10-26T18:00:00").toISOString(), now)).toBe("Monday")
		expect(threadTime(dayjs("2026-10-22T18:00:00").toISOString(), now)).toBe("Thursday")
		expect(threadTime(dayjs("2026-10-21T18:00:00").toISOString(), now)).toBe("10/21/2026")
	})

	it("is the date for a time ahead of the clock, and nothing for no time", () => {
		setActivePinia(createPinia())
		expect(threadTime(dayjs("2026-10-30T10:00:00").toISOString(), now)).toBe("10/30/2026")
		expect(threadTime("not a date", now)).toBe("")
	})
})

describe("the inbox's search", () => {
	it("finds the text in the title or the organization, ignoring case and accents", () => {
		expect(threadMatches("Réseau suspect", "Acme Corp", "reseau")).toBe(true)
		expect(threadMatches("Phishing click", "Acme Corp", "ACME")).toBe(true)
		expect(threadMatches("Phishing click", "Acme Corp", "  ")).toBe(true)
		expect(threadMatches("Phishing click", "Acme Corp", "ransom")).toBe(false)
	})
})
