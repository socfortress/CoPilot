import type { ApiError } from "@/types/common"
import type { IocEnrichment, IocSourceResult } from "@/types/iocEnrichment"
import { describe, expect, it } from "vitest"
import i18n from "@/lang"
import {
	byIocId,
	checkFailureMessage,
	engineSegments,
	enginesFlagged,
	hasAnswer,
	hasDetails,
	kindNote,
	sourceStatusText,
	toneOf,
	VERDICT_META,
	verdictKey,
	verdictLabel,
	virusTotalLink
} from "../iocEnrichment"

function source(overrides: Partial<IocSourceResult> = {}): IocSourceResult {
	return {
		source: "virustotal",
		status: "not_checked",
		verdict: null,
		checked_at: null,
		error: null,
		virustotal: null,
		opencti: null,
		...overrides
	}
}

function ioc(overrides: Partial<IocEnrichment> = {}): IocEnrichment {
	return {
		ioc_id: 1,
		value: "45.155.205.233",
		type: "IP",
		kind: "ip",
		verdict: null,
		checked_at: null,
		can_check: true,
		next_check_at: null,
		sources: [source(), source({ source: "opencti" })],
		...overrides
	}
}

function failure(status?: number): ApiError {
	return { response: status ? { status, data: { message: "server text" } } : undefined } as unknown as ApiError
}

/** The IOCs' Threat Intel (#1318): how verdicts and sources read, and what a failed check says. */
describe("ioc enrichment helpers", () => {
	it("reads an IOC never checked as unchecked, and every verdict with a word, a colour and an icon", () => {
		expect(verdictKey(ioc())).toBe("unchecked")
		expect(verdictKey(ioc({ verdict: "malicious" }))).toBe("malicious")
		for (const [key, meta] of Object.entries(VERDICT_META)) {
			expect(verdictLabel(key as keyof typeof VERDICT_META)).not.toMatch(/^iocEnrichment\./)
			expect(meta.icon).toMatch(/^carbon:/)
		}
		expect(VERDICT_META.malicious.type).toBe("error")
		expect(VERDICT_META.suspicious.type).toBe("warning")
		expect(VERDICT_META.clean.type).toBe("success")
	})

	it("reads a value never sent anywhere as not sent, whatever is stored", () => {
		expect(verdictKey(ioc({ kind: "internal" }))).toBe("not_sent")
		expect(verdictKey(ioc({ kind: "invalid", verdict: "malicious" }))).toBe("not_sent")
		expect(verdictLabel("not_sent")).toBe("Not sent")
	})

	it("draws each verdict in its status colour, and the rest in a neutral ink", () => {
		expect(toneOf("malicious")).toBe("error")
		expect(toneOf("suspicious")).toBe("warning")
		expect(toneOf("known")).toBe("info")
		expect(toneOf("clean")).toBe("success")
		expect(["unknown", "not_found", "unchecked", "not_sent", null].map(v => toneOf(v as never))).toEqual([
			"neutral",
			"neutral",
			"neutral",
			"neutral",
			"neutral"
		])
	})

	it("splits VirusTotal's engines into the meter's segments, worst first, skipping the empty ones", () => {
		const details = {
			malicious: 9,
			suspicious: 0,
			harmless: 61,
			undetected: 24,
			engines: 100,
			reputation: null,
			last_analysis_at: null,
			tags: [],
			country: null,
			as_owner: null,
			type_description: null,
			link: null
		}
		expect(engineSegments(details).map(s => [s.key, s.percent])).toEqual([
			["malicious", 9],
			["harmless", 61],
			["undetected", 24]
		])
		expect(engineSegments({ ...details, engines: 0, malicious: 0, harmless: 0, undetected: 0 })).toEqual([])
	})

	it("says why a private address or a bad value is looked up nowhere", () => {
		expect(kindNote("internal")).toContain("never sent")
		expect(kindNote("invalid")).toContain("can't be looked up")
		expect(kindNote("ip")).toBeNull()
		expect(kindNote("other")).toBeNull()
	})

	it("words each source's state, and a failure without the source's own text", () => {
		expect(sourceStatusText(source({ status: "not_checked" }))).toBe("Not checked yet")
		expect(sourceStatusText(source({ status: "unsupported" }))).toBe("Can't look up this kind of value")
		expect(sourceStatusText(source({ status: "error", error: "rate_limited" }))).toBe(
			"VirusTotal is busy. Try again in a minute."
		)
		expect(sourceStatusText(source({ source: "opencti", status: "error", error: "unavailable" }))).toBe(
			"Could not be reached. Try again later."
		)
		expect(hasAnswer(source({ status: "found" }))).toBe(true)
		expect(hasAnswer(source({ status: "not_found" }))).toBe(true)
		expect(hasAnswer(source({ status: "error" }))).toBe(false)
	})

	it("offers details only for a source that answered with some", () => {
		expect(hasDetails(ioc())).toBe(false)
		expect(hasDetails(ioc({ sources: [source({ status: "not_found" })] }))).toBe(false)
		const details = {
			malicious: 2,
			suspicious: 1,
			harmless: 50,
			undetected: 10,
			engines: 63,
			reputation: null,
			last_analysis_at: null,
			tags: [],
			country: null,
			as_owner: null,
			type_description: null,
			link: null
		}
		expect(hasDetails(ioc({ sources: [source({ status: "found", verdict: "suspicious", virustotal: details })] }))).toBe(
			true
		)
		expect(enginesFlagged(details)).toBe(3)
	})

	it("links only to a page on VirusTotal", () => {
		expect(virusTotalLink("https://www.virustotal.com/gui/ip-address/8.8.8.8")).toBe(
			"https://www.virustotal.com/gui/ip-address/8.8.8.8"
		)
		expect(virusTotalLink("javascript:alert(1)")).toBeNull()
		expect(virusTotalLink("https://www.virustotal.com.evil.example/gui/x")).toBeNull()
		expect(virusTotalLink("https://www.virustotal.com/gui/ x")).toBeNull()
		expect(virusTotalLink(null)).toBeNull()
	})

	it("tells each refusal of a check by its status, never the server's text", () => {
		expect(checkFailureMessage(failure(403))).toBe("Threat Intel checks are not enabled for your organization.")
		expect(checkFailureMessage(failure(404))).toBe("This IOC is no longer on the alert.")
		expect(checkFailureMessage(failure(409))).toBe("This IOC is already being checked. Try again in a moment.")
		expect(checkFailureMessage(failure(429))).toContain("daily limit")
		expect(checkFailureMessage(failure(500))).toBe("The IOC could not be checked. Try again later.")
		expect(checkFailureMessage(failure())).not.toContain("server text")
	})

	it("keys the IOCs by id", () => {
		expect(Object.keys(byIocId([ioc({ ioc_id: 4 }), ioc({ ioc_id: 9 })]))).toEqual(["4", "9"])
	})

	it("speaks the user's language", () => {
		i18n.global.locale.value = "it"
		expect(verdictLabel("malicious")).toBe("Malevolo")
		expect(checkFailureMessage(failure(409))).toBe("Questo IOC è già in verifica. Riprova tra un momento.")
		expect(sourceStatusText(source({ source: "opencti", status: "error", error: "unavailable" }))).toBe(
			"Non raggiungibile. Riprova più tardi."
		)
	})
})
