import type { UbaEntityDetail, UbaRiskHistory, UbaTenantStatus } from "@/types/uba"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, ref } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"
import { buildRiskChartOption } from "../risk-chart"
import UbaAlertDetailView from "../UbaAlertDetail.vue"
import UbaBacktestsView from "../UbaBacktests.vue"
import UbaEntityDetailView from "../UbaEntityDetail.vue"
import UbaSuppressionsView from "../UbaSuppressions.vue"
import RiskMeter from "../ui/RiskMeter.vue"
import SignalTimeline from "../ui/SignalTimeline.vue"
import UbaDrawerHeader from "../ui/UbaDrawerHeader.vue"
import UbaStatusStrip from "../ui/UbaStatusStrip.vue"
import UbaToolbar from "../ui/UbaToolbar.vue"
import { requesterOrigin, riskTone, shortError, suppressionOrigin } from "../utils"

const api = {
	getBacktests: vi.fn(),
	getRuleCatalog: vi.fn(),
	getSuppressions: vi.fn(),
	removeSuppressions: vi.fn(),
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

	it("puts its actions at the end of the tags row, even with no tags", () => {
		const wrapper = mount(
			defineComponent({
				setup: () => () =>
					h(NMessageProvider, null, {
						default: () =>
							h(
								UbaDrawerHeader,
								{ meta: { kind: "UBA alert", icon: "carbon:warning-alt", title: "A" } },
								{ actions: () => h("button", "Open page") }
							)
					})
			})
		)
		expect(wrapper.findAll("[data-testid=uba-drawer-tag]")).toHaveLength(0)
		expect(wrapper.get("[data-testid=uba-drawer-actions]").text()).toBe("Open page")
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
		identity: {
			privileged: true,
			privileged_reasons: [],
			memberships: [],
			aliases: [
				{ type: "netbios_sam", value: "CONTOSO\\administrator" },
				{ type: "sid", value: "S-1-5-21-1-2-3-500" },
				{ type: "something_new", value: "x-1" }
			],
			kind: "human",
			shadow: true
		},
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

		// Aliases: the kind in one column, the value in the next.
		const aliases = wrapper.get("[data-testid=uba-identity-aliases]")
		const kinds = aliases.findAll(".alias-type").map(k => k.text())
		const values = aliases.findAll(".alias-value").map(v => v.text())
		expect(kinds).toEqual(["netbios_sam", "sid", "something_new"])
		expect(values).toEqual(["CONTOSO\\administrator", "S-1-5-21-1-2-3-500", "x-1"])

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

describe("ubaToolbar", () => {
	it("keeps the explanation behind a button and a short summary in line, so it stays one row", async () => {
		const wrapper = mount(UbaToolbar, {
			attachTo: document.body,
			slots: {
				default: () => h("button", "Open"),
				summary: () => "1 open alert",
				hint: () => "UBA alerts open when an entity's accumulated risk passes 100."
			}
		})
		expect(wrapper.get("[data-testid=uba-toolbar-summary]").text()).toBe("1 open alert")
		// The long text is not printed in the row; it opens from "How it works".
		expect(wrapper.text()).not.toContain("accumulated risk")
		await wrapper.get("[data-testid=uba-toolbar-hint]").trigger("click")
		await flushPromises()
		expect(document.body.querySelector("[data-testid=uba-toolbar-hint-text]")?.textContent).toContain("accumulated risk")
		wrapper.unmount()
	})

	it("shows no right side when there is nothing to summarise or explain", () => {
		const wrapper = mount(UbaToolbar, { slots: { default: () => h("button", "Open") } })
		expect(wrapper.find("[data-testid=uba-toolbar-summary]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=uba-toolbar-hint]").exists()).toBe(false)
	})
})

describe("suppressionOrigin", () => {
	it("reads CoPilot's reasons and sources in words", () => {
		expect(suppressionOrigin("added by ana via copilot", "api:ana via copilot")).toEqual({
			why: "Suppressed by hand",
			by: "ana",
			via: "CoPilot"
		})
		expect(
			suppressionOrigin("api:ana via copilot: false positive (EXPECTED_ACTIVITY)", "api:ana via copilot")
		).toEqual({ why: "False positive · Expected activity", by: "ana", via: "CoPilot" })
		expect(suppressionOrigin("api:ana: false positive (no reason)", "api:ana").why).toBe("False positive")
		// Anything else is kept, without repeating its source.
		expect(suppressionOrigin("worker: noisy on this host", "worker")).toEqual({
			why: "noisy on this host",
			by: null,
			via: "worker"
		})
		expect(suppressionOrigin(null, null)).toEqual({ why: "Suppressed", by: null, via: null })
	})
})

describe("ubaSuppressions", () => {
	it("names each entity, says when the mute ends and why, and opens the entity", async () => {
		api.getSuppressions.mockResolvedValue({
			data: {
				suppressions: [
					{
						tenant_id: "lab",
						entity_key: "eb93-key",
						rule_id: "auth.failures_then_success",
						until: new Date(Date.now() + 30 * 86_400_000).toISOString(),
						reason: "added by ana via copilot",
						source: "api:ana via copilot",
						created_at: new Date().toISOString(),
						active: true
					}
				]
			}
		})
		api.getEntity.mockResolvedValue({ data: { entity_name: "CONTOSO\\Administrator", entity_type: "actor" } })
		const opened: string[] = []
		const wrapper = withProviders(UbaSuppressionsView, { customerCode: "lab" }, { onOpenEntity: (k: string) => opened.push(k) })
		await flushPromises()
		// One lookup per entity: suppressions carry only the key.
		expect(api.getEntity).toHaveBeenCalledOnce()
		const row = wrapper.get(".n-data-table-tbody .n-data-table-tr")
		expect(row.text()).toContain("CONTOSO\\Administrator")
		expect(row.text()).toContain("eb93-key")
		expect(row.text()).toContain("in a month")
		expect(row.text()).toContain("Suppressed by hand")
		expect(row.text()).toContain("by ana · via CoPilot")
		expect(wrapper.get("[data-testid=uba-toolbar-summary]").text()).toBe("1 active")
		await row.get("button").trigger("click")
		expect(opened).toEqual(["eb93-key"])
	})
})

describe("backtest helpers", () => {
	it("says who asked for a run and from where", () => {
		expect(requesterOrigin("ana via copilot")).toEqual({ by: "ana", via: "CoPilot" })
		expect(requesterOrigin("uba-admin")).toEqual({ by: "uba-admin", via: null })
		expect(requesterOrigin(null)).toEqual({ by: null, via: null })
	})

	it("cuts a UBA error to its first message, keeping balanced parentheses", () => {
		const connection =
			"ConnectionError: ConnectionError(Cannot connect to host indexer:9200 ssl:default [Connect call failed ('10.0.0.1', 9200)]) caused by: ClientConnectorError(Cannot connect to host indexer:9200)"
		expect(shortError(connection)).toBe("ConnectionError: Cannot connect to host indexer:9200")
		expect(shortError("TransportError(429, too many requests)")).toBe("TransportError(429, too many requests)")
		expect(shortError("ValueError: bad filter")).toBe("ValueError: bad filter")
		expect(shortError(`ValueError: ${"x".repeat(200)}`, 20)).toHaveLength(20)
		expect(shortError(null)).toBe("")
	})
})

describe("ubaBacktests", () => {
	const job = (over: Record<string, unknown>) => ({
		id: "j",
		status: "done",
		params: { days: 1, warmup_days: 0 },
		requested_by: "ana via copilot",
		created_at: new Date(Date.now() - 120_000).toISOString(),
		started_at: "2026-10-06T10:00:00Z",
		finished_at: "2026-10-06T10:00:04Z",
		progress: {},
		error: null,
		result: null,
		...over
	})

	it("lists runs with their window as chips, a status with an icon and one line of detail", async () => {
		api.getRuleCatalog.mockResolvedValue({ data: { rules: [] } })
		api.getBacktests.mockResolvedValue({
			data: {
				backtests: [
					job({ id: "a", params: { days: 3, warmup_days: 7, rules: ["auth.x", "auth.y"], filter: "eventID:4720" } }),
					job({
						id: "b",
						status: "error",
						error: "ConnectionError: ConnectionError(Cannot connect to host indexer:9200 ssl:default [x]) caused by: y"
					}),
					job({ id: "c", status: "queued", started_at: null, finished_at: null })
				]
			}
		})
		const wrapper = withProviders(UbaBacktestsView, { customerCode: "lab" })
		await flushPromises()
		const rows = wrapper.findAll("[data-testid=uba-backtest-runs] .n-data-table-tbody .n-data-table-tr")
		expect(rows).toHaveLength(3)
		const flat = (n: number) => rows[n].text().replace(/\s+/g, " ")

		expect(flat(0)).toContain("2 minutes ago")
		expect(flat(0)).toContain("ana via CoPilot")
		expect(rows[0].findAll(".param-chip").map(c => c.text().trim())).toEqual(["3 days", "+7 d warm-up", "2 rules", "filter"])
		expect(flat(0)).toContain("done")
		expect(flat(0)).toContain("took 4 s")
		expect(flat(0)).toContain("View result")

		// A failure reads as one short line; the whole message is behind "Details".
		expect(flat(1)).toContain("failed")
		expect(flat(1)).toContain("ConnectionError: Cannot connect to host indexer:9200")
		expect(flat(1)).not.toContain("caused by")
		expect(rows[1].find("[data-testid=uba-backtest-error-details]").exists()).toBe(true)

		expect(flat(2)).toContain("queued")
		expect(flat(2)).toContain("Cancel")
		expect(flat(2)).toContain("all rules")
	})
})
