import type { Alert } from "@/types/alerts"
import type { IocEnrichment, IocSourceResult } from "@/types/iocEnrichment"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { useIocEnrichmentAvailability } from "@/composables/common/useIocEnrichmentAvailability"
import i18n from "@/lang"
import AlertIocs from "../AlertIocs.vue"

const getAvailability = vi.hoisted(() => vi.fn())
const getForAlert = vi.hoisted(() => vi.fn())
const check = vi.hoisted(() => vi.fn())
vi.mock("@/api", () => ({ default: { iocEnrichment: { getAvailability, getForAlert, check } } }))

const ALERT = {
	id: 7,
	customer_code: "ACME",
	iocs: [
		{ id: 1, value: "45.155.205.233", type: "IP", description: "" },
		{ id: 2, value: "10.1.2.3", type: "IP", description: "Internal host" },
		{ id: 3, value: "<img src=x onerror=alert(1)>", type: "OTHER", description: "" }
	]
} as unknown as Alert

const VT_FOUND: IocSourceResult = {
	source: "virustotal",
	status: "found",
	verdict: "malicious",
	checked_at: "2026-10-28T08:00:00Z",
	error: null,
	virustotal: {
		malicious: 9,
		suspicious: 0,
		harmless: 61,
		undetected: 24,
		engines: 94,
		reputation: -55,
		last_analysis_at: "2026-10-27T08:00:00Z",
		tags: ["scanner"],
		country: "NL",
		as_owner: "Example Hosting",
		type_description: null,
		link: "https://www.virustotal.com/gui/ip-address/45.155.205.233"
	},
	opencti: null
}

const CTI_FOUND: IocSourceResult = {
	source: "opencti",
	status: "found",
	verdict: "suspicious",
	checked_at: "2026-10-28T08:00:00Z",
	error: null,
	virustotal: null,
	opencti: {
		score: 55,
		entity_types: ["IPv4-Addr"],
		labels: ["botnet"],
		indicators: [{ name: "C2 server", score: 55, valid_until: "2027-01-01T00:00:00Z", revoked: false }],
		reports: [{ name: "Weekly botnet digest", published: "2026-10-01T00:00:00Z" }],
		withheld: 2
	}
}

function result(source: "virustotal" | "opencti", status: IocSourceResult["status"], extra: Partial<IocSourceResult> = {}) {
	return { source, status, verdict: null, checked_at: null, error: null, virustotal: null, opencti: null, ...extra }
}

function enrichment(ioc_id: number, value: string, overrides: Partial<IocEnrichment> = {}): IocEnrichment {
	return {
		ioc_id,
		value,
		type: "IP",
		kind: "ip",
		verdict: null,
		checked_at: null,
		can_check: true,
		next_check_at: null,
		sources: [result("virustotal", "not_checked"), result("opencti", "not_checked")],
		...overrides
	}
}

const UNCHECKED = [
	enrichment(1, "45.155.205.233"),
	enrichment(2, "10.1.2.3", {
		kind: "internal",
		can_check: false,
		sources: [result("virustotal", "internal"), result("opencti", "internal")]
	}),
	enrichment(3, "<img src=x onerror=alert(1)>", {
		kind: "other",
		sources: [result("virustotal", "unsupported"), result("opencti", "not_configured")]
	})
]

const CHECKED = enrichment(1, "45.155.205.233", {
	verdict: "malicious",
	checked_at: "2026-10-28T08:00:00Z",
	can_check: false,
	next_check_at: "2026-10-29T08:00:00Z",
	sources: [VT_FOUND, CTI_FOUND]
})

function render() {
	return mount(defineComponent({ render: () => h(NMessageProvider, () => h(AlertIocs, { alert: ALERT })) }), {
		attachTo: document.body
	})
}

/** A line's text as a reader sees it: HTML collapses the template's whitespace. */
function read(element: { text: () => string }) {
	return element.text().replace(/\s+/g, " ")
}

function card(wrapper: ReturnType<typeof render>, id: number) {
	return wrapper.get(`[data-testid=ioc-ti][data-ioc="${id}"]`)
}

beforeEach(() => {
	setActivePinia(createPinia())
	useIocEnrichmentAvailability().reset()
	getAvailability.mockReset().mockResolvedValue({ data: { enabled: true, sources: ["virustotal", "opencti"] } })
	getForAlert.mockReset().mockResolvedValue({ data: { alert_id: 7, iocs: UNCHECKED, sources: ["virustotal", "opencti"] } })
	check.mockReset()
})

/** The alert's IOCs with the SOC's Threat Intel (#1318). */
describe("alert iocs: threat intel", () => {
	it("shows the IOCs alone, and asks nothing more, when the customer has it off", async () => {
		getAvailability.mockResolvedValue({ data: { enabled: false, sources: [] } })
		const wrapper = render()
		await flushPromises()
		expect(getAvailability).toHaveBeenCalledWith("ACME")
		expect(getForAlert).not.toHaveBeenCalled()
		expect(wrapper.findAll("[data-testid=alert-ioc]")).toHaveLength(3)
		expect(wrapper.find("[data-testid=ioc-ti]").exists()).toBe(false)
	})

	it("reads what the SOC keeps when the alert opens, and offers a check per IOC", async () => {
		const wrapper = render()
		await flushPromises()
		expect(getForAlert).toHaveBeenCalledWith(7, expect.any(AbortSignal))
		const first = card(wrapper, 1)
		expect(read(first.get("[data-testid=ioc-ti-verdict]"))).toBe("Not checked")
		expect(first.get("[data-testid=ioc-ti-check]").text()).toBe("Check")
		expect(first.findAll("[data-testid=ioc-ti-source]").map(read)).toEqual([
			"VirusTotal Not checked yet",
			"OpenCTI Not checked yet"
		])
		expect(check).not.toHaveBeenCalled()
	})

	it("explains why a private address is never sent, with no check to press", async () => {
		const wrapper = render()
		await flushPromises()
		const internal = card(wrapper, 2)
		expect(internal.get("[data-testid=ioc-ti-verdict]").attributes("data-verdict")).toBe("not_sent")
		expect(read(internal.get("[data-testid=ioc-ti-verdict]"))).toBe("Not sent")
		expect(internal.get("[data-testid=ioc-ti-kind]").text()).toContain("never sent")
		expect(internal.find("[data-testid=ioc-ti-check]").exists()).toBe(false)
		expect(internal.find("[data-testid=ioc-ti-sources]").exists()).toBe(false)
	})

	it("hides a source the SOC can't ask, and shows every value as text", async () => {
		const wrapper = render()
		await flushPromises()
		const other = card(wrapper, 3)
		expect(other.findAll("[data-testid=ioc-ti-source]").map(line => line.attributes("data-source"))).toEqual([
			"virustotal"
		])
		expect(wrapper.find("img").exists()).toBe(false)
		expect(wrapper.text()).toContain("<img src=x onerror=alert(1)>")
	})

	it("checks an IOC and shows the verdict, each source's answer and the details", async () => {
		check.mockResolvedValue({ data: { ioc: CHECKED } })
		const wrapper = render()
		await flushPromises()
		await card(wrapper, 1).get("[data-testid=ioc-ti-check]").trigger("click")
		await flushPromises()
		expect(check).toHaveBeenCalledWith(7, 1)
		const checked = card(wrapper, 1)
		expect(checked.get("[data-testid=ioc-ti-verdict]").attributes("data-verdict")).toBe("malicious")
		expect(read(checked.get("[data-testid=ioc-ti-verdict]"))).toBe("Malicious")
		expect(checked.find("[data-testid=ioc-ti-check]").exists()).toBe(false)
		expect(checked.get("[data-testid=ioc-ti-next]").text()).toContain("Can be checked again after")
		expect(checked.findAll("[data-testid=ioc-ti-source]").map(read)).toEqual([
			"VirusTotal Malicious Flagged by 9 of 94 engines",
			"OpenCTI Suspicious Score 55"
		])

		// The meters: VirusTotal's engines by answer (only what flagged it in colour), OpenCTI's score.
		const meter = checked.get("[data-source=virustotal] .ti-meter")
		expect(meter.attributes("role")).toBe("img")
		expect(meter.attributes("aria-label")).toBe("Flagged by 9 of 94 engines")
		expect(meter.findAll(".ti-meter-part").map(part => part.classes().find(c => c.startsWith("ti-meter-part--")))).toEqual([
			"ti-meter-part--malicious",
			"ti-meter-part--harmless",
			"ti-meter-part--undetected"
		])
		expect(checked.get("[data-source=opencti] .ti-meter-fill").attributes("style")).toContain("width: 55%")
		expect(checked.classes()).toContain("ti--error")

		await checked.get("[data-testid=ioc-ti-toggle]").trigger("click")
		const details = card(wrapper, 1).get("[data-testid=ioc-ti-details]")
		expect(details.text()).toContain("Example Hosting")
		expect(details.get("[data-testid=ioc-ti-vt-tags]").text()).toContain("scanner")
		const link = details.get("[data-testid=ioc-ti-vt-link]")
		expect(link.attributes("href")).toBe("https://www.virustotal.com/gui/ip-address/45.155.205.233")
		expect(link.attributes("rel")).toBe("noopener noreferrer")
		expect(link.attributes("target")).toBe("_blank")
		expect(details.get("[data-testid=ioc-ti-cti-indicators]").text()).toContain("C2 server")
		expect(details.get("[data-testid=ioc-ti-cti-reports]").text()).toContain("Weekly botnet digest")
		expect(read(details.get("[data-testid=ioc-ti-cti-withheld]"))).toBe("2 items withheld by their sharing marking")
	})

	it("says why a check was refused, by its status", async () => {
		check.mockRejectedValue({ response: { status: 429, data: { detail: "limit text from the server" } } })
		const wrapper = render()
		await flushPromises()
		await card(wrapper, 1).get("[data-testid=ioc-ti-check]").trigger("click")
		await flushPromises()
		const failure = card(wrapper, 1).get("[data-testid=ioc-ti-failure]").text()
		expect(failure).toContain("daily limit of IOC checks")
		expect(failure).not.toContain("from the server")
		expect(card(wrapper, 1).find("[data-testid=ioc-ti-check]").exists()).toBe(true)
	})

	it("keeps an older answer beside a failed refresh", async () => {
		getForAlert.mockResolvedValue({
			data: {
				alert_id: 7,
				iocs: [
					enrichment(1, "45.155.205.233", {
						verdict: "malicious",
						checked_at: "2026-10-26T08:00:00Z",
						sources: [{ ...VT_FOUND, error: "unavailable" }, result("opencti", "error", { error: "unavailable" })]
					})
				],
				sources: ["virustotal", "opencti"]
			}
		})
		const wrapper = render()
		await flushPromises()
		const lines = card(wrapper, 1).findAll("[data-testid=ioc-ti-source]")
		expect(lines[0].get("[data-testid=ioc-ti-refresh-failed]").text()).toContain("Could not be checked again")
		expect(read(lines[1])).toBe("OpenCTI Could not be reached. Try again later.")
		expect(card(wrapper, 1).get("[data-testid=ioc-ti-check]").text()).toBe("Check again")
	})

	it("offers to try again when the results can't be read", async () => {
		getForAlert.mockRejectedValueOnce({ response: { status: 500, data: {} }, message: "" })
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get("[data-testid=ioc-ti-load-error]").text()).toContain("could not be loaded")
		await wrapper.get("[data-testid=ioc-ti-load-error] button").trigger("click")
		await flushPromises()
		expect(wrapper.find("[data-testid=ioc-ti-load-error]").exists()).toBe(false)
		expect(wrapper.findAll("[data-testid=ioc-ti]")).toHaveLength(3)
	})

	it("speaks the user's language", async () => {
		i18n.global.locale.value = "it"
		check.mockResolvedValue({ data: { ioc: CHECKED } })
		const wrapper = render()
		await flushPromises()
		expect(card(wrapper, 1).get("[data-testid=ioc-ti-check]").text()).toBe("Verifica")
		await card(wrapper, 1).get("[data-testid=ioc-ti-check]").trigger("click")
		await flushPromises()
		expect(read(card(wrapper, 1).get("[data-testid=ioc-ti-verdict]"))).toBe("Malevolo")
		expect(read(card(wrapper, 1).findAll("[data-testid=ioc-ti-source]")[0])).toContain("Segnalato da 9 motori su 94")
	})
})
