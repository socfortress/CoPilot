/**
 * The evidence views (OP-3), mounted with realistic evidence from talon-analyst's job modules: what
 * each shows, every value as text, links only from plain agent ids, and `disk_forecast`'s chart (an
 * admin's: it reads the job's runs; anyone else sees the numbers only, and nothing is read).
 */
import type { TalonOpsEvidenceValue } from "@/types/talonOps"
import { enableAutoUnmount, flushPromises, mount, RouterLinkStub } from "@vue/test-utils"
import { AxiosError, AxiosHeaders } from "axios"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { GIB } from "../evidence/evidence"
import OpsEvidence from "../evidence/OpsEvidence.vue"

const listRuns = vi.fn()

vi.mock("@/api", () => ({
	default: { talonOps: { listRuns: (...args: unknown[]) => listRuns(...args) } }
}))

/** The chart, as a div carrying its aria-label and its option. */
let lastOption: Record<string, unknown> | null = null
vi.mock("vue-echarts", async () => {
	const vue = await import("vue")
	return {
		default: vue.defineComponent({
			props: { option: { type: Object, required: true } },
			setup: (props, { attrs }) => () => {
				lastOption = props.option as Record<string, unknown>
				return vue.h("div", { "data-testid": attrs["data-testid"], "aria-label": attrs["aria-label"], role: attrs.role })
			}
		})
	}
})

const XSS = "<img src=x onerror=alert(1)>"

function render(job: string, kind: string, evidence: unknown, props: Record<string, unknown> = {}) {
	return mount(OpsEvidence, {
		props: { finding: { job, kind, evidence: evidence as Record<string, TalonOpsEvidenceValue> | null }, ...props },
		global: {
			stubs: { RouterLink: RouterLinkStub, Icon: true }
		}
	})
}

function byId(wrapper: ReturnType<typeof render>, id: string) {
	return wrapper.find(`[data-testid="${id}"]`)
}

function texts(wrapper: ReturnType<typeof render>, id: string) {
	return wrapper.findAll(`[data-testid="${id}"]`).map(n => n.text())
}

enableAutoUnmount(afterEach)

beforeEach(() => {
	setActivePinia(createPinia())
	listRuns.mockReset()
	lastOption = null
})

describe("agent_hygiene", () => {
	it("lists the agents, links the plain ids, and counts the rest", () => {
		const wrapper = render("agent_hygiene", "wazuh_version", {
			agent_version: "v4.7.0",
			manager_version: "v4.14.7",
			agents: 27,
			critical_assets: 1,
			sample_agents: [
				{ agent_id: "001", agent_name: XSS, critical_asset: true },
				{ agent_id: "../x", agent_name: "web", critical_asset: false }
			],
			agents_more: 25
		})
		const rows = wrapper.findAll('[data-testid="talon-ops-evidence-agent"]')
		expect(rows).toHaveLength(2)
		expect(rows[0].text()).toContain(XSS)
		expect(rows[0].find("img").exists()).toBe(false)
		expect(rows[0].text()).toContain("v4.7.0")
		expect(rows[0].text()).toContain("yes")
		expect(rows[1].text()).toContain("no")
		const links = wrapper.findAllComponents(RouterLinkStub)
		expect(links.map(l => l.props("to"))).toEqual([{ name: "Agent", params: { id: "001" } }])
		expect(byId(wrapper, "talon-ops-evidence-agents-more").text()).toBe("+25 more")
	})

	it("renders nothing for evidence without agents", () => {
		expect(render("agent_hygiene", "wazuh_version", { sample_agents: "x" }).html()).not.toContain("talon-ops-evidence")
	})
})

describe("quiet_endpoints", () => {
	it("shows the conditions as tags and both last-seen times", () => {
		const wrapper = render("quiet_endpoints", "wazuh_quiet", {
			agent_id: "001",
			agent_name: "dc-01",
			critical_asset: true,
			conditions: ["wazuh_quiet", "velociraptor_quiet"],
			wazuh_last_seen: "2026-10-20T12:00:00+00:00",
			wazuh_days_quiet: 7,
			velociraptor_last_seen: null
		})
		expect(texts(wrapper, "talon-ops-evidence-condition")).toEqual(["Wazuh quiet", "Velociraptor quiet"])
		const wazuh = byId(wrapper, "talon-ops-evidence-seen-wazuh")
		expect(wazuh.find("time").attributes("title")).toBe("2026-10-20 12:00 UTC")
		expect(wazuh.text()).toContain("ago")
		expect(wazuh.text()).toContain("quiet for 7 days")
		expect(byId(wrapper, "talon-ops-evidence-seen-velociraptor").text()).toContain("Never, or not known")
		expect(byId(wrapper, "talon-ops-figure-critical_asset").text()).toBe("yes")
	})

	it("renders nothing for malformed evidence", () => {
		expect(render("quiet_endpoints", "wazuh_quiet", { conditions: 3 }).html()).not.toContain("talon-ops-evidence")
	})
})

describe("mapping_drift", () => {
	it("field_limit: a bar of the fields used against the limit", () => {
		const wrapper = render("mapping_drift", "field_limit", {
			index_pattern: "wazuh-acme_*",
			index: "wazuh-acme_12",
			mapped_fields: 960,
			total_fields_limit: 1000,
			lower_bound: true
		})
		const limit = byId(wrapper, "talon-ops-evidence-field-limit")
		expect(limit.text()).toContain("At least 960 fields of a limit of 1,000")
		expect(limit.text()).toContain("96%")
		expect(limit.text()).toContain("A lower bound")
	})

	it("type_conflict and talon_fields: tables; field_growth: before → after", () => {
		const conflict = render("mapping_drift", "type_conflict", {
			conflicts: { "data.port": ["keyword", "long"] },
			talon_fields_conflicting: ["data.port"],
			conflicts_total: 3
		})
		expect(texts(conflict, "talon-ops-evidence-row")[0]).toContain("keyword, long")
		expect(texts(conflict, "talon-ops-evidence-row")[0]).toContain("Talon relies on it")
		expect(byId(conflict, "talon-ops-evidence-more").text()).toBe("+2 more")

		const talon = render("mapping_drift", "talon_fields", {
			problems: [{ field: "timestamp", problem: "type", mapped: { timestamp: ["keyword"] }, needs: ["date"] }]
		})
		expect(texts(talon, "talon-ops-evidence-row")[0]).toMatch(/timestamp\s*Wrong type\s*timestamp: keyword\s*date/)

		const growth = render("mapping_drift", "field_growth", { family_field_count: 1500, baseline_family_field_count: 1000 })
		expect(byId(growth, "talon-ops-evidence-field-growth").text()).toMatch(/1,000\s*→\s*1,500/)
	})
})

describe("storage_usage and noisy_events", () => {
	it("storage_usage: bars per family for GB stored and GB per day", () => {
		const wrapper = render("storage_usage", "large_footprint", {
			total_size_gb: 612.4,
			gb_per_day_7d: 4.2,
			families: [
				{ index_pattern: "wazuh-acme_*", size_gb: 600, gb_per_day_7d: 4 },
				{ index_pattern: XSS, size_gb: 12.4, gb_per_day_7d: 0.2 }
			]
		})
		const bars = texts(wrapper, "talon-ops-evidence-bar")
		expect(bars).toHaveLength(4)
		expect(bars[0]).toMatch(/wazuh-acme_\*\s*600\.0 GB/)
		expect(bars[1]).toContain(XSS)
		expect(wrapper.find("img").exists()).toBe(false)
		expect(byId(wrapper, "talon-ops-figure-total_size_gb").text()).toBe("612.4 GB")
	})

	it("noisy_events: the share, its GB/day and the floor", () => {
		const wrapper = render("noisy_events", "tuning_candidate", {
			share: 0.42,
			estimated_gb_per_day: 0.8,
			gb_floor: 0.5,
			customer_gb_per_day: 2
		})
		expect(byId(wrapper, "talon-ops-evidence-share").text()).toBe("42%")
		expect(texts(wrapper, "talon-ops-evidence-bar").join(" | ")).toMatch(/This candidate\s*0\.80 GB\/day.*floor it passed\s*0\.50 GB\/day/)
	})
})

describe("exclusion_candidates", () => {
	it("shows the verdicts, the guards and the manager-wide note", () => {
		const wrapper = render("exclusion_candidates", "exclusion_candidate", {
			asset_name: "dc-01",
			alerts: 40,
			verdicted: 25,
			false_positive_verdicts: 25,
			rule_wide: { lookback_days: 90, true_positive: 0, escalated: 1 },
			host_scoped: false
		})
		expect(byId(wrapper, "talon-ops-evidence-manager-wide").text()).toContain("every agent on the Wazuh manager")
		expect(byId(wrapper, "talon-ops-evidence-verdict-false_positive").text()).toContain("25")
		expect(byId(wrapper, "talon-ops-evidence-verdict-true_positive").text()).toContain("0")
		expect(byId(wrapper, "talon-ops-evidence-verdict-undetermined").text()).toContain("15")
		expect(byId(wrapper, "talon-ops-evidence-guard-true_positive").attributes("data-passed")).toBe("true")
		expect(byId(wrapper, "talon-ops-evidence-guard-escalated").attributes("data-passed")).toBe("false")
		expect(byId(wrapper, "talon-ops-evidence-guard-escalated").text()).toContain("1 found")
	})

	it("has no manager-wide note unless host_scoped is false", () => {
		const wrapper = render("exclusion_candidates", "exclusion_candidate", { alerts: 40 })
		expect(byId(wrapper, "talon-ops-evidence-manager-wide").exists()).toBe(false)
	})
})

describe("cluster_health and silent_log_sources", () => {
	it("shows key figures with units", () => {
		const cluster = render("cluster_health", "disk_watermark", {
			node: "node-1",
			used_pct: 91.2,
			avail_gb: 88.1,
			total_gb: 1000,
			thresholds_used_pct: { low: 85, high: 90, flood_stage: 95 },
			threshold_enabled: true
		})
		expect(byId(cluster, "talon-ops-figure-used_pct").text()).toBe("91.2%")
		expect(byId(cluster, "talon-ops-figure-avail_gb").text()).toBe("88.10 GB")
		expect(byId(cluster, "talon-ops-figure-thresholds_used_pct.flood_stage").text()).toBe("95%")
		expect(byId(cluster, "talon-ops-figure-threshold_enabled").text()).toBe("yes")

		const silent = render("silent_log_sources", "silent", {
			source: "fortigate",
			last_hour: 0,
			median: 1200,
			newest_event: "2026-10-24T06:00:00+00:00",
			hours_since_newest: 30.04
		})
		expect(byId(silent, "talon-ops-figure-median").text()).toBe("1,200")
		expect(byId(silent, "talon-ops-figure-hours_since_newest").text()).toBe("30 hours")
		expect(byId(silent, "talon-ops-figure-newest_event").attributes("title")).toBe("2026-10-24 06:00 UTC")
	})
})

describe("disk_forecast", () => {
	const evidence = {
		node: XSS,
		used_gb: 700,
		total_gb: 1000,
		used_pct: 70,
		slope_gb_per_day: 20,
		days_to_low: 7.5,
		days_to_high: 10,
		days_to_flood_stage: null,
		thresholds_used_pct: { low: 85, high: 90, flood_stage: 95 }
	}

	function run(at: string, used: number) {
		return {
			id: at,
			job: "disk_forecast",
			customer_code: null,
			tick: at,
			status: "ok",
			finished_at: at,
			detail: { tick: at, nodes: { [XSS]: { used: used * GIB, total: 1000 * GIB } } }
		}
	}

	function runs(...items: ReturnType<typeof run>[]) {
		listRuns.mockImplementation(() => Promise.resolve({ data: { success: true, message: "", dropped: 0, items } }))
	}

	it("shows a non-admin the numbers only, and reads no runs", async () => {
		const wrapper = render("disk_forecast", "disk_forecast", evidence, { isAdmin: false })
		await flushPromises()
		expect(listRuns).not.toHaveBeenCalled()
		expect(byId(wrapper, "talon-ops-disk-admins-only").exists()).toBe(true)
		expect(byId(wrapper, "talon-ops-disk-used").text()).toMatch(/700\.0 GB of 1,000\.0 GB\s*\(70%\)/)
		expect(byId(wrapper, "talon-ops-disk-slope").text()).toBe("20.00 GB/day")
		expect(byId(wrapper, "talon-ops-disk-low").text()).toMatch(/85%\s*\(850\.0 GB\)\s*·\s*in about 7\.5 days/)
		expect(byId(wrapper, "talon-ops-disk-flood_stage").text()).toContain("not forecast")
		expect(byId(wrapper, "talon-ops-disk-node").text()).toBe(XSS)
		expect(wrapper.find("img").exists()).toBe(false)
	})

	it("draws an admin's chart from the job's runs, the node name as text", async () => {
		runs(run("2026-10-26T04:45:00Z", 700), run("2026-10-25T04:45:00Z", 680), run("2026-10-25T01:00:00Z", 679))
		const wrapper = render("disk_forecast", "disk_forecast", evidence, { isAdmin: true, settings: { horizon_days: 30 } })
		await flushPromises()
		expect(listRuns).toHaveBeenCalledWith({ job: "disk_forecast", limit: 30 }, expect.anything())
		const chart = byId(wrapper, "talon-ops-disk-chart")
		expect(chart.attributes("role")).toBe("img")
		expect(chart.attributes("aria-label")).toContain(`Used disk on ${XSS}`)
		expect(chart.attributes("aria-label")).toContain("(2 days)")
		expect(wrapper.find("img").exists()).toBe(false)
		const formatter = (lastOption?.tooltip as { formatter: (p: unknown) => string }).formatter
		const html = formatter({ seriesName: "Used", value: [Date.parse("2026-10-26T04:45:00Z"), 700] })
		expect(html).not.toContain("<img")
		expect(html).toContain("&lt;img src=x onerror=alert(1)&gt;")
	})

	it("shows the numbers only with fewer than two days of samples", async () => {
		runs(run("2026-10-26T04:45:00Z", 700), run("2026-10-26T01:00:00Z", 699))
		const wrapper = render("disk_forecast", "disk_forecast", evidence, { isAdmin: true })
		await flushPromises()
		expect(byId(wrapper, "talon-ops-disk-few").exists()).toBe(true)
		expect(byId(wrapper, "talon-ops-disk-chart").exists()).toBe(false)
	})

	it("says when the runs can't be read, and still shows the numbers", async () => {
		const headers = new AxiosHeaders()
		listRuns.mockImplementation(() =>
			Promise.reject(
				new AxiosError("x", "ERR", undefined, undefined, {
					status: 502,
					statusText: "",
					data: { detail: "Talon didn't answer", code: "unavailable" },
					headers,
					config: { headers }
				})
			)
		)
		const wrapper = render("disk_forecast", "disk_forecast", evidence, { isAdmin: true })
		await flushPromises()
		expect(byId(wrapper, "talon-ops-disk-error").text()).toContain("Talon didn't answer")
		expect(byId(wrapper, "talon-ops-disk-slope").exists()).toBe(true)
	})
})
