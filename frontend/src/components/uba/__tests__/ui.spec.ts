import type { UbaEntityDetail, UbaRiskHistory, UbaTenantStatus } from "@/types/uba"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, ref } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"
import { buildRiskChartOption } from "../risk-chart"
import UbaAlertDetailView from "../UbaAlertDetail.vue"
import UbaEntityDetailView from "../UbaEntityDetail.vue"
import RiskMeter from "../ui/RiskMeter.vue"
import SignalTimeline from "../ui/SignalTimeline.vue"
import UbaDrawerHeader from "../ui/UbaDrawerHeader.vue"
import UbaStatusStrip from "../ui/UbaStatusStrip.vue"
import { riskTone } from "../utils"

const api = {
	submitFeedback: vi.fn(),
	getAlert: vi.fn(),
	getEntity: vi.fn(),
	getEntityTimeline: vi.fn(),
	getEntityRiskHistory: vi.fn(),
	getSignalEvidence: vi.fn()
}
vi.mock("@/api", () => ({
	default: { uba: new Proxy({}, { get: (_, name: string) => (...args: unknown[]) => api[name as keyof typeof api](...args) }) }
}))
const copy = vi.hoisted(() => vi.fn())
vi.mock("@vueuse/core", async importOriginal => ({
	...(await importOriginal<typeof import("@vueuse/core")>()),
	useClipboard: () => ({ copy, copied: ref(false) })
}))
// Charts are covered through their option; here they only need to mount.
vi.mock("vue-echarts", () => ({ default: defineComponent({ setup: () => () => h("div", { class: "v-chart" }) }) }))

const STYLE: Record<string, string> = {
	"fg-default-color": "#eee",
	"fg-secondary-color": "#aaa",
	"fg-tertiary-color": "#777",
	"border-color": "#333",
	"bg-default-color": "#111",
	"font-family": "sans-serif",
	"primary-color": "#fc0"
}

function withProviders(component: unknown, props: Record<string, unknown> = {}, listeners: Record<string, unknown> = {}) {
	const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/", component: { render: () => null } }] })
	return mount(
		defineComponent({
			setup: () => () => h(NMessageProvider, null, { default: () => h(component as never, { ...props, ...listeners }) })
		}),
		{ global: { plugins: [router] } }
	)
}

beforeEach(() => {
	setActivePinia(createPinia())
	for (const mock of Object.values(api)) mock.mockReset()
})

describe("riskTone", () => {
	it("bands risk against the customer's alert threshold", () => {
		expect([10, 40, 100, 160].map(r => riskTone(r))).toEqual(["neutral", "info", "warning", "error"])
		// A customer that alerts at 50 sees the same risk as more serious.
		expect([10, 40, 100].map(r => riskTone(r, 50))).toEqual(["neutral", "info", "error"])
	})
})

describe("riskMeter", () => {
	it("prints the risk in its band's colour over a track that runs to twice the threshold", () => {
		const wrapper = mount(RiskMeter, { props: { risk: 150, threshold: 100 } })
		expect(wrapper.get("[data-testid=risk-meter-value]").text()).toBe("150")
		expect(wrapper.get("[data-testid=risk-meter-value]").classes()).toContain("text-error")
		expect(wrapper.get(".track > span").attributes("style")).toContain("width: 75%")
		expect(wrapper.get(".notch").attributes("style")).toContain("left: 50%")
		expect(wrapper.get("[role=meter]").attributes("aria-label")).toBe("Risk 150, alert at 100")
	})

	it("caps the bar, and spells out its scale when it is the headline figure", () => {
		const wrapper = mount(RiskMeter, { props: { risk: 500, threshold: 100, size: "lg" } })
		expect(wrapper.get(".track > span").attributes("style")).toContain("width: 100%")
		expect(wrapper.text()).toContain("alert 100")
		expect(wrapper.text()).toContain("200")
	})
})

describe("ubaDrawerHeader", () => {
	it("holds its height with a skeleton until the item loads", () => {
		const wrapper = withProviders(UbaDrawerHeader, { meta: null, kind: "Entity" })
		expect(wrapper.get("[data-testid=uba-drawer-kind]").text()).toBe("Entity")
		expect(wrapper.find(".n-skeleton").exists()).toBe(true)
		expect(wrapper.find("[data-testid=risk-meter]").exists()).toBe(false)
	})

	it("names the item, offers its key to copy, and leads with its risk", async () => {
		copy.mockResolvedValue(undefined)
		const wrapper = withProviders(UbaDrawerHeader, {
			meta: {
				kind: "Entity · user",
				icon: "carbon:user",
				title: "CONTOSO\\Administrator",
				key: "eb93-key",
				keyLabel: "Entity key",
				risk: 182,
				threshold: 100,
				tags: [{ label: "privileged", type: "warning" }]
			}
		})
		expect(wrapper.get("[data-testid=uba-drawer-title]").text()).toBe("CONTOSO\\Administrator")
		expect(wrapper.get("[data-testid=risk-meter-value]").text()).toBe("182")
		expect(wrapper.findAll("[data-testid=uba-drawer-tag]").map(t => t.text())).toEqual(["privileged"])
		await wrapper.get("[data-testid=uba-drawer-copy]").trigger("click")
		await flushPromises()
		expect(copy).toHaveBeenCalledWith("eb93-key")
	})
})

describe("signalTimeline", () => {
	it("puts each finding on the rail with what it added, dimming the muted ones", () => {
		const wrapper = withProviders(SignalTimeline, {
			customerCode: "lab",
			items: [
				{ key: "a", time: "2026-10-06T14:00:00Z", ruleId: "auth.failures_then_success", explanation: "Logged on after 34 failures", points: 50, signalId: "s1", evidenceCount: 1 },
				{ key: "b", time: "2026-10-06T13:00:00Z", ruleId: "wazuh:60115", explanation: "Locked out", points: 0, native: true, muted: true },
				{ key: "c", time: "2026-10-06T12:00:00Z", ruleId: null, explanation: "An update" }
			]
		})
		const items = wrapper.findAll("[data-testid=signal-item]")
		expect(items).toHaveLength(3)
		expect(items[0].get("[data-testid=signal-points]").text()).toBe("+50")
		expect(items[0].get("[data-testid=signal-points]").classes()).toContain("text-error")
		expect(items[0].text()).toContain("Show events (1)")
		expect(items[1].classes()).toContain("is-muted")
		expect(items[1].text()).toContain("native")
		// An alert update carries no points and no evidence of its own.
		expect(items[2].find("[data-testid=signal-points]").exists()).toBe(false)
		expect(items[2].text()).not.toContain("Show events")
	})
})

describe("ubaStatusStrip", () => {
	const status = {
		open_alerts: 2,
		alerts_24h: 3,
		signals_24h: 12,
		lag_seconds: 900,
		feeds: [{ source: "wazuh", status: "stale", lag_p50_s: 3000, received_1h: 0, repeated_1h: 0, reasons: ["no events for 50 min"] }],
		agents: { total: 5, reporting: 3, not_reporting: 1, retired: 1, never_connected: 0, not_reporting_hosts: [] }
	} as unknown as UbaTenantStatus

	it("shows one cell per figure, and colours only what needs a look", () => {
		const wrapper = withProviders(UbaStatusStrip, { status })
		const value = (key: string) => wrapper.get(`[data-testid=uba-status-${key}] [data-testid=uba-status-value]`)
		expect(value("open-alerts").text()).toBe("2")
		expect(value("open-alerts").classes()).toContain("text-error")
		expect(value("alerts-24h").classes()).not.toContain("text-error")
		expect(value("lag").text()).toBe("15 min")
		expect(value("lag").classes()).toContain("text-warning")
		expect(value("feed-wazuh").text()).toBe("stale")
		expect(value("computers").text()).toBe("3/4")
		expect(wrapper.get("[data-testid=uba-status-strip]").attributes("style")).toContain("--cells: 6")
	})
})

describe("risk chart", () => {
	const history = {
		alert_threshold: 100,
		points: [
			{ time: "2026-10-06T12:00:00Z", risk: 40, native: 0 },
			{ time: "2026-10-06T13:00:00Z", risk: 120, native: 0 }
		],
		alerts: []
	} as unknown as UbaRiskHistory

	it("uses the platform's multi-series tooltip, without a Wazuh row when there is no Wazuh risk", () => {
		const option = buildRiskChartOption(history, STYLE, true) as { tooltip: { formatter: (p: unknown) => string } }
		const html = option.tooltip.formatter([{ dataIndex: 1 }])
		// The title band and padded rows of formatChartTooltipAxisMultiSeries.
		expect(html).toContain("padding:4px 8px")
		expect(html).toContain("risk <b")
		expect(html).toContain("UBA findings: <b>120</b>")
		expect(html).not.toContain("Wazuh alerts")
	})
})

describe("ubaEntityDetail", () => {
	const detail: UbaEntityDetail = {
		tenant: "lab",
		entity_key: "eb93-key",
		entity_type: "actor",
		entity_name: "CONTOSO\\Administrator",
		risk: 182,
		risk_by_rule: [
			{ rule_id: "auth.failures_then_success", risk: 50, signals: 1, native: false },
			{ rule_id: "wazuh:60154", risk: 25, signals: 1, native: true }
		],
		identity: { privileged: true, privileged_reasons: [], memberships: [], aliases: [], kind: "human", shadow: true },
		host: null,
		alerts: [{ id: "al1", opened_at: "2026-10-06T14:00:00Z", risk: 107, verdict: null, copilot_alert_id: null }],
		suppressions: []
	} as unknown as UbaEntityDetail

	it("tells the drawer's header who it is, how risky, and what qualifies it", async () => {
		api.getEntity.mockResolvedValue({ data: detail })
		api.getEntityTimeline.mockResolvedValue({
			data: {
				total: 1,
				signals: [
					{ id: "s1", time: "2026-10-06T14:00:00Z", rule_id: "auth.failures_then_success", explanation: "x", effective_score: 50, native: false, suppressed: false, evidence: [] }
				]
			}
		})
		api.getEntityRiskHistory.mockResolvedValue({ data: { alert_threshold: 80, points: [], alerts: [] } })
		const metas: unknown[] = []
		const wrapper = withProviders(UbaEntityDetailView, { customerCode: "lab", entityKey: "eb93-key" }, { onMeta: (m: unknown) => metas.push(m) })
		await flushPromises()
		expect(metas.at(-1)).toMatchObject({
			kind: "Entity · user",
			title: "CONTOSO\\Administrator",
			key: "eb93-key",
			risk: 182,
			threshold: 80,
			tags: [
				{ label: "privileged", type: "warning" },
				{ label: "open alert", type: "error" }
			]
		})
		// Rules compare against the strongest one; the timeline lists the findings on the rail.
		const rows = wrapper.findAll("[data-testid=uba-rule-row]")
		expect(rows).toHaveLength(2)
		expect(rows[0].get(".share-track > span").attributes("style")).toContain("width: 100%")
		expect(rows[1].get(".share-track > span").attributes("style")).toContain("width: 50%")
		expect(wrapper.findAll("[data-testid=signal-item]")).toHaveLength(1)

		// The whole alert row opens the alert, by click or by keyboard.
		const opened: string[] = []
		const view = withProviders(UbaEntityDetailView, { customerCode: "lab", entityKey: "eb93-key" }, { onOpenAlert: (id: string) => opened.push(id) })
		await flushPromises()
		const row = view.get("[data-testid=uba-entity-alert]")
		expect(row.attributes("role")).toBe("button")
		await row.trigger("click")
		await row.trigger("keydown", { key: "Enter" })
		expect(opened).toEqual(["al1", "al1"])
		expect(row.text()).toContain("open")
	})
})

describe("ubaAlertDetail", () => {
	beforeEach(() => {
		api.getAlert.mockResolvedValue({
			data: {
				alert: {
					id: "al1",
					entity_key: "eb93-key",
					entity_type: "actor",
					entity_name: "CONTOSO\\Administrator",
					opened_at: "2026-10-06T14:00:00Z",
					risk: 107,
					reason: "accumulated risk 107 >= 100",
					rules: [],
					update_count: 0,
					verdict: null,
					copilot_alert_id: null
				},
				signals: [],
				updates: []
			}
		})
	})

	it("opens the entity from anywhere on the summary box", async () => {
		const entities: string[] = []
		const wrapper = withProviders(UbaAlertDetailView, { customerCode: "lab", alertId: "al1" }, { onOpenEntity: (k: string) => entities.push(k) })
		await flushPromises()
		const box = wrapper.get("[data-testid=uba-alert-entity]")
		expect(box.attributes("role")).toBe("button")
		expect(box.text()).toContain("accumulated risk 107")
		await box.trigger("click")
		await box.trigger("keydown", { key: " " })
		expect(entities).toEqual(["eb93-key", "eb93-key"])
	})

	it("asks for the verdict with two choice buttons, then what a false positive needs", async () => {
		const wrapper = withProviders(UbaAlertDetailView, { customerCode: "lab", alertId: "al1" })
		await flushPromises()
		expect(wrapper.get("[data-testid=uba-verdict]").attributes("role")).toBe("radiogroup")
		const falsePositive = wrapper.get("[data-testid=uba-verdict-FALSE_POSITIVE]")
		expect(falsePositive.attributes("aria-checked")).toBe("false")
		await falsePositive.trigger("click")
		expect(falsePositive.attributes("aria-checked")).toBe("true")
		expect(falsePositive.classes()).toContain("is-selected")
		expect(wrapper.text()).toContain("Suppress the rules behind this alert")
		await wrapper.get("[data-testid=uba-verdict-TRUE_POSITIVE]").trigger("click")
		expect(wrapper.text()).not.toContain("Suppress the rules behind this alert")
	})

	it("asks for confirmation before saving, since a verdict cannot be changed afterwards", async () => {
		api.submitFeedback.mockResolvedValue({ data: { suppressed_rules: ["auth.x"] } })
		const wrapper = withProviders(UbaAlertDetailView, { customerCode: "lab", alertId: "al1" })
		await flushPromises()
		await wrapper.get("[data-testid=uba-verdict-FALSE_POSITIVE]").trigger("click")
		const why = wrapper.findComponent({ name: "Select" })
		why.vm.$emit("update:value", "EXPECTED_ACTIVITY")
		await flushPromises()

		const confirm = () => document.body.querySelector("[data-testid=uba-verdict-confirm]")
		await wrapper.get("[data-testid=uba-verdict-save]").trigger("click")
		await flushPromises()
		// Clicking Save only opens the confirmation; nothing is sent yet.
		expect(api.submitFeedback).not.toHaveBeenCalled()
		expect(confirm()?.textContent).toContain("stop adding risk for this entity for 30 days")
		expect(confirm()?.textContent).toContain("cannot be changed afterwards")

		const buttons = [...document.body.querySelectorAll<HTMLButtonElement>(".n-popconfirm__action button")]
		buttons.find(b => b.textContent?.includes("Cancel"))?.click()
		await flushPromises()
		expect(api.submitFeedback).not.toHaveBeenCalled()

		await wrapper.get("[data-testid=uba-verdict-save]").trigger("click")
		await flushPromises()
		const save = [...document.body.querySelectorAll<HTMLButtonElement>(".n-popconfirm__action button")].find(b =>
			b.textContent?.includes("Save false positive")
		)
		save?.click()
		await flushPromises()
		expect(api.submitFeedback).toHaveBeenCalledWith("lab", "al1", {
			verdict: "FALSE_POSITIVE",
			reason: "EXPECTED_ACTIVITY",
			note: null,
			suppress: true
		})
	})

	it("words the confirmation for a true positive without the suppression", async () => {
		const wrapper = withProviders(UbaAlertDetailView, { customerCode: "lab", alertId: "al1" })
		await flushPromises()
		await wrapper.get("[data-testid=uba-verdict-TRUE_POSITIVE]").trigger("click")
		await wrapper.get("[data-testid=uba-verdict-save]").trigger("click")
		await flushPromises()
		const text = document.body.querySelector("[data-testid=uba-verdict-confirm]")?.textContent ?? ""
		expect(text).toContain("Save this alert as a true positive?")
		expect(text).not.toContain("30 days")
	})
})
