import type { OpenCTIObservable, OpenCTIObservableLookup } from "@/types/opencti"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { ref } from "vue"
import OpenCTILookupResult from "../OpenCTILookupResult.vue"

const platformUrl = ref<string | null>("http://opencti:8080")

vi.mock("@/composables/useOpenCTIAvailability", () => ({
	useOpenCTIAvailability: () => ({
		objectUrl: (id: string) => (platformUrl.value ? `${platformUrl.value}/dashboard/id/${id}` : null)
	})
}))

function observable(over: Partial<OpenCTIObservable> = {}): OpenCTIObservable {
	return {
		id: "obs-1",
		standard_id: "ipv4-addr--1",
		entity_type: "IPv4-Addr",
		created_at: "2026-09-16T00:00:00Z",
		updated_at: "2026-09-16T00:00:00Z",
		created_by: "AlienVault",
		labels: [{ value: "botnet", color: "#c72922" }],
		markings: ["TLP:CLEAR"],
		value: "212.193.31.122",
		description: null,
		score: 60,
		file_name: null,
		hashes: [],
		indicators: [
			{
				id: "ind-1",
				standard_id: "indicator--1",
				entity_type: "Indicator",
				created_at: null,
				updated_at: null,
				created_by: null,
				labels: [],
				markings: [],
				name: "212.193.31.122",
				description: null,
				pattern: "[ipv4-addr:value = '212.193.31.122']",
				pattern_type: "stix",
				main_observable_type: "IPv4-Addr",
				score: 60,
				confidence: 100,
				valid_from: null,
				valid_until: "2099-01-01T00:00:00Z",
				revoked: false
			}
		],
		indicators_count: 1,
		reports: [{ id: "rep-1", name: "An Evolution of the Botnet", published: "2026-09-01T00:00:00Z" }],
		reports_count: 1,
		...over
	}
}

function lookup(over: Partial<OpenCTIObservableLookup> = {}): OpenCTIObservableLookup {
	return { value: "212.193.31.122", found: true, total: 1, observables: [observable()], ...over }
}

function render(result: OpenCTIObservableLookup) {
	return mount(OpenCTILookupResult, { props: { lookup: result } })
}

describe("openCTILookupResult", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		platformUrl.value = "http://opencti:8080"
	})

	it("says so when OpenCTI has never seen the value", () => {
		const wrapper = render(lookup({ value: "8.8.8.8", found: false, total: 0, observables: [] }))
		expect(wrapper.text()).toContain("8.8.8.8")
		expect(wrapper.text()).toContain("is not in OpenCTI")
	})

	it("shows score, marking, author, labels, indicator and report", () => {
		const text = render(lookup()).text()
		for (const expected of [
			"IPv4-Addr",
			"212.193.31.122",
			"60",
			"TLP:CLEAR",
			"by AlienVault",
			"botnet",
			"Indicators (1)",
			"[ipv4-addr:value = '212.193.31.122']",
			"Reports (1)",
			"An Evolution of the Botnet"
		]) {
			expect(text).toContain(expected)
		}
	})

	it("links objects to OpenCTI's by-id route", () => {
		const hrefs = render(lookup())
			.findAll("a")
			.map(a => a.attributes("href"))
		expect(hrefs).toEqual(
			expect.arrayContaining([
				"http://opencti:8080/dashboard/id/ind-1",
				"http://opencti:8080/dashboard/id/rep-1",
				"http://opencti:8080/dashboard/id/obs-1"
			])
		)
	})

	it("renders plain text rather than dead links when the platform URL is unknown", () => {
		platformUrl.value = null
		const wrapper = render(lookup())
		expect(wrapper.findAll("a")).toHaveLength(0)
		expect(wrapper.text()).toContain("An Evolution of the Botnet")
		expect(wrapper.text()).not.toContain("Open in OpenCTI")
	})

	it("flags expired indicators", () => {
		const indicators = observable().indicators.map(i => ({ ...i, valid_until: "2001-01-01T00:00:00Z" }))
		const text = render(lookup({ observables: [observable({ indicators })] })).text()
		expect(text).toContain("expired")
		expect(text).not.toContain("revoked")
	})

	it("flags revoked indicators, and revocation wins over expiry", () => {
		const indicators = observable().indicators.map(i => ({
			...i,
			valid_until: "2001-01-01T00:00:00Z",
			revoked: true
		}))
		const text = render(lookup({ observables: [observable({ indicators })] })).text()
		expect(text).toContain("revoked")
		expect(text).not.toContain("expired")
	})

	it("notes when more observables match than were returned", () => {
		const text = render(lookup({ total: 3 })).text()
		expect(text).toContain("Showing 1 of 3 matching observables")
	})
})
