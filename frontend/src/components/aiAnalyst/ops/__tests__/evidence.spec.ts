/**
 * The Ops drawer's evidence readers (OP-3): the unit formatters, each job's reader on realistic
 * evidence (the shapes of talon-analyst's job modules) and on malformed evidence (null: the generic
 * list), `disk_forecast`'s points from the job's runs (one per UTC day, the latest), its chart (fewer
 * than two points: none) and its tooltip, which escapes every value.
 */
import type { TalonOpsEvidenceValue, TalonOpsRun } from "@/types/talonOps"
import { describe, expect, it } from "vitest"
import { buildDiskChart, diskTooltip } from "../evidence/disk-chart"
import {
	agentHygieneView,
	bytesText,
	countText,
	daysText,
	diskForecastView,
	diskPoints,
	exclusionView,
	figures,
	gbPerDayText,
	gbText,
	GIB,
	growthText,
	hoursText,
	mappingDriftView,
	minutesText,
	noisyEventsView,
	pctText,
	projectionDays,
	quietEndpointsView,
	ratioText,
	relativeText,
	scheduledTimeOfDay,
	SILENT_LOG_SOURCES_FIGURES,
	storageUsageView,
	timeParts,
	unitText,
	utcText,
	viewKind,
	yesNo
} from "../evidence/evidence"
import { afterResolved, findingRuns } from "../ops"

const XSS = "<img src=x onerror=alert(1)>"

function must<T>(value: T | null): T {
	if (value === null) throw new Error("expected a value")
	return value
}
const NOW = Date.parse("2026-10-27T12:00:00Z")

describe("the unit formatters", () => {
	it("shows GB with 1 or 2 decimals, bytes as 1024-based GB", () => {
		expect(gbText(12.345)).toBe("12.35 GB")
		expect(gbText(512.34)).toBe("512.3 GB")
		expect(gbText(0)).toBe("0.00 GB")
		expect(bytesText(600 * GIB)).toBe("600.0 GB")
		expect(bytesText(1.5 * GIB)).toBe("1.50 GB")
		expect(gbPerDayText(2.5)).toBe("2.50 GB/day")
		expect(gbText(null)).toBe("—")
		expect(gbText(Number.NaN)).toBe("—")
	})

	it("shows ratios and percentages as %", () => {
		expect(ratioText(0.824)).toBe("82.4%")
		expect(ratioText(1)).toBe("100%")
		expect(pctText(85)).toBe("85%")
		expect(pctText(62.47)).toBe("62.5%")
		expect(ratioText(null)).toBe("—")
	})

	it("shows days, hours, minutes and counts with their unit", () => {
		expect(daysText(4.46)).toBe("4.5 days")
		expect(daysText(1)).toBe("1 day")
		expect(daysText(0)).toBe("0 days")
		expect(hoursText(1)).toBe("1 hour")
		expect(hoursText(36.25)).toBe("36.3 hours")
		expect(minutesText(42.4)).toBe("42 minutes")
		expect(countText(12345)).toBe("12,345")
		expect(daysText(undefined)).toBe("—")
	})

	it("shows booleans as yes or no", () => {
		expect(yesNo(true)).toBe("yes")
		expect(yesNo(false)).toBe("no")
		expect(yesNo("true")).toBe("—")
	})

	it("shows an ISO time as local time, its UTC form and how long ago", () => {
		const parts = timeParts("2026-10-24T06:00:00.123456+00:00", NOW)
		expect(parts?.utc).toBe("2026-10-24 06:00 UTC")
		expect(parts?.relative).toBe("3 days ago")
		expect(parts?.local).toMatch(/^\w{3} \d{1,2}, \d{2}:\d{2}$/)
		expect(timeParts("yesterday", NOW)).toBeNull()
		expect(timeParts(42, NOW)).toBeNull()
		expect(relativeText(NOW + 2 * 3600_000, NOW)).toBe("in 2 hours")
		expect(relativeText(NOW - 30_000, NOW)).toBe("just now")
		expect(utcText(Date.parse("2026-01-02T03:04:05Z"))).toBe("2026-01-02 03:04 UTC")
	})

	it("reads a figure only when its value has its unit's type", () => {
		expect(unitText("12", "gb")).toBeNull()
		expect(unitText(true, "count")).toBeNull()
		expect(unitText(3, "bool")).toBeNull()
		expect(unitText("2026-10-24T06:00:00Z", "time")?.title).toBe("2026-10-24 06:00 UTC")
		expect(figures({ last_hour: 0, median: "x", hours_since_newest: 30.04 }, SILENT_LOG_SOURCES_FIGURES)).toEqual([
			{ key: "last_hour", label: "Events in the last hour", text: "0" },
			{ key: "hours_since_newest", label: "Since the newest event", text: "30 hours" }
		])
	})
})

describe("agent_hygiene", () => {
	const agents: TalonOpsEvidenceValue[] = [
		{ agent_id: "001", agent_name: "dc-01", critical_asset: true },
		{ agent_id: "../../users", agent_name: null, critical_asset: false },
		"junk",
		{ agent_name: "no id" }
	]

	it("lists a wazuh_version group's agents with the group's version, linked by plain ids", () => {
		const view = agentHygieneView(
			{ agent_version: "v4.7.0", manager_version: "v4.14.7", agents: 27, critical_assets: 1, sample_agents: agents, agents_more: 2 },
			"wazuh_version"
		)
		expect(view?.rows.map(r => [r.id, r.hostname, r.version, r.critical, r.to])).toEqual([
			["001", "dc-01", "v4.7.0", true, { name: "Agent", params: { id: "001" } }],
			["../../users", null, "v4.7.0", false, null]
		])
		expect(view?.more).toBe(2)
		expect(view?.hasVersion).toBe(true)
		expect(view?.figures.map(f => f.text)).toEqual(["v4.14.7", "v4.7.0", "27", "1"])
	})

	it("reads velociraptor_version's agents under `behind`, each with its own version", () => {
		const view = agentHygieneView(
			{
				newest_version: "0.73.2",
				behind: { agents: 1, critical_assets: 0, sample_agents: [{ agent_id: "002", agent_name: "web" }], agents_more: 0 },
				behind_versions: { "002": "0.7.4" }
			},
			"velociraptor_version"
		)
		expect(view?.rows[0].version).toBe("0.7.4")
		expect(view?.more).toBe(0)
	})

	it("has no version column for velociraptor_missing, and no view without agents", () => {
		expect(agentHygieneView({ sample_agents: agents }, "velociraptor_missing")?.hasVersion).toBe(false)
		expect(agentHygieneView({ sample_agents: "x" }, "wazuh_version")).toBeNull()
		expect(agentHygieneView({ sample_agents: [{ agent_name: "x" }] }, "wazuh_version")).toBeNull()
		expect(agentHygieneView(null, "wazuh_version")).toBeNull()
	})
})

describe("quiet_endpoints", () => {
	it("reads the conditions and the last-seen times", () => {
		const view = quietEndpointsView(
			{
				agent_id: "001",
				conditions: ["wazuh_quiet", "velociraptor_quiet"],
				wazuh_last_seen: "2026-10-20T12:00:00+00:00",
				wazuh_days_quiet: 7,
				velociraptor_last_seen: null,
				velociraptor_days_quiet: null
			},
			NOW
		)
		expect(view?.conditions.map(c => c.label)).toEqual(["Wazuh quiet", "Velociraptor quiet"])
		expect(view?.seen[0].time?.relative).toBe("7 days ago")
		expect(view?.seen[1].time).toBeNull()
	})

	it("has no view without conditions or times", () => {
		expect(quietEndpointsView({ conditions: [1, 2], agent_id: "001" })).toBeNull()
		expect(quietEndpointsView({ wazuh_last_seen: "never" })).toBeNull()
	})
})

describe("mapping_drift", () => {
	it("field_limit: fields used against the limit", () => {
		const view = mappingDriftView(
			{ index_pattern: "wazuh-acme_*", index: "wazuh-acme_12", mapped_fields: 950, total_fields_limit: 1000, lower_bound: false },
			"field_limit"
		)
		expect(view).toMatchObject({ kind: "field_limit", used: 950, limit: 1000, percent: 95 })
		expect(mappingDriftView({ mapped_fields: 950, total_fields_limit: 0 }, "field_limit")).toBeNull()
		expect(mappingDriftView({ mapped_fields: "950", total_fields_limit: 1000 }, "field_limit")).toBeNull()
	})

	it("type_conflict: field and types, Talon's marked", () => {
		const view = mappingDriftView(
			{ conflicts: { "data.port": ["keyword", "long"], bad: 3 }, talon_fields_conflicting: ["data.port"], conflicts_total: 5 },
			"type_conflict"
		)
		expect(view?.kind === "type_conflict" && view.rows).toEqual([{ field: "data.port", types: "keyword, long", talon: true }])
		expect(view?.kind === "type_conflict" && view.more).toBe(4)
		expect(mappingDriftView({ conflicts: [] }, "type_conflict")).toBeNull()
	})

	it("field_growth: before and after", () => {
		expect(
			mappingDriftView({ family_field_count: 1500, baseline_family_field_count: 1000, growth: 1.5 }, "field_growth")
		).toMatchObject({ before: 1000, after: 1500 })
		const growth = mappingDriftView({ family_field_count: 1300, baseline_family_field_count: 1000, growth: 1.3 }, "field_growth")
		expect(growth?.figures.find(f => f.key === "growth")?.text).toBe("+30%")
		expect(growthText(0.9)).toBe("−10%")
		expect(growthText(null)).toBe("—")
		expect(mappingDriftView({ family_field_count: 1500 }, "field_growth")).toBeNull()
	})

	it("talon_fields: field and problem", () => {
		const view = mappingDriftView(
			{
				problems: [
					{ field: "timestamp", problem: "type", mapped: { timestamp: ["keyword"] }, needs: ["date", "date_nanos"] },
					{ field: "agent_labels_customer", problem: "missing", mapped: {}, needs: ["keyword"] },
					{ problem: "missing" }
				]
			},
			"talon_fields"
		)
		expect(view?.kind === "talon_fields" && view.rows).toEqual([
			{ field: "timestamp", problem: "Wrong type", mapped: "timestamp: keyword", needs: "date, date_nanos" },
			{ field: "agent_labels_customer", problem: "Missing", mapped: "—", needs: "keyword" }
		])
		expect(mappingDriftView({ problems: {} }, "talon_fields")).toBeNull()
		expect(mappingDriftView({ x: 1 }, "some_new_kind")).toBeNull()
	})
})

describe("storage_usage and noisy_events", () => {
	it("storage_usage: GB stored and GB/day per family as bars", () => {
		const view = storageUsageView({
			total_size_gb: 120.5,
			gb_per_day_7d: 3.2,
			families: [
				{ index_pattern: "wazuh-acme_*", size_gb: 100, gb_per_day_7d: 3 },
				{ index_pattern: "graylog-acme_*", size_gb: 20.5, gb_per_day_7d: null },
				{ size_gb: 1 }
			],
			families_more: 3
		})
		expect(view?.groups[0].bars.map(b => [b.label, b.text, b.width])).toEqual([
			["wazuh-acme_*", "100.0 GB", 100],
			["graylog-acme_*", "20.50 GB", 20.5]
		])
		expect(view?.groups[1].bars.map(b => b.text)).toEqual(["3.00 GB/day"])
		expect(view?.more).toBe(3)
		expect(storageUsageView({ families: [{ index_pattern: "x" }] })).toBeNull()
	})

	it("noisy_events: the share, GB/day and the floor", () => {
		const view = noisyEventsView({ share: 0.4213, estimated_gb_per_day: 0.8, gb_floor: 0.5, customer_gb_per_day: 2 })
		expect(view?.share).toBeCloseTo(42.13)
		expect(view?.groups[0].bars.map(b => [b.label, b.text])).toEqual([
			["This candidate", "0.80 GB/day"],
			["The floor it passed", "0.50 GB/day"],
			["The customer, all measured", "2.00 GB/day"]
		])
		expect(noisyEventsView({ share: "42%", estimated_gb_per_day: 0.8 })).toBeNull()
	})
})

describe("exclusion_candidates", () => {
	const evidence = {
		alert_name: "Logon failure",
		asset_name: "dc-01",
		alerts: 40,
		closed: 30,
		verdicted: 25,
		false_positive_verdicts: 24,
		rule_wide: { lookback_days: 90, true_positive: 0, escalated: 0, cases: 0, bas_alerts: 0, critical_asset_alerts: 2 },
		host_scoped: false
	}

	it("counts the verdicts, lists the guards and flags a manager-wide rule", () => {
		const view = exclusionView(evidence)
		expect(view?.verdicts.map(v => [v.label, v.text])).toEqual([
			["False positive", "24"],
			["True positive", "1"],
			["Undetermined (no verdict)", "15"]
		])
		expect(view?.guards.map(g => [g.key, g.passed])).toEqual([
			["true_positive", true],
			["escalated", true],
			["cases", true],
			["bas_alerts", true],
			["critical_asset_alerts", false]
		])
		expect(view?.guards[0].label).toContain("90 days")
		expect(view?.managerWide).toBe(true)
	})

	it("never fills in a count it can't compute", () => {
		const view = exclusionView({ alerts: 10, rule_wide: { true_positive: "none" } })
		expect(view?.verdicts.map(v => v.text)).toEqual(["—", "—", "—"])
		expect(view?.guards).toEqual([{ key: "true_positive", label: "No true-positive verdict on the rule", passed: null, count: null }])
		expect(view?.managerWide).toBe(false)
		expect(exclusionView({ alert_name: "x" })).toBeNull()
	})
})

describe("disk_forecast", () => {
	const evidence = {
		node: "node-1",
		used_gb: 700,
		total_gb: 1000,
		used_pct: 70,
		slope_gb_per_day: 20,
		days_to_low: 7.5,
		days_to_high: 10,
		days_to_flood_stage: 12.5,
		thresholds_used_pct: { low: 85, high: 90, flood_stage: 95 }
	}

	function run(at: string, nodes: unknown, overrides: Partial<TalonOpsRun> = {}): TalonOpsRun {
		return {
			id: at,
			job: "disk_forecast",
			job_version: 1,
			customer_code: null,
			tick: at,
			triggered_by: "schedule",
			status: "ok",
			collected: true,
			explained: null,
			candidates: 1,
			new: 0,
			updated: 1,
			resolved: 0,
			error: null,
			cost_usd: null,
			duration_ms: 1,
			started_at: at,
			finished_at: at,
			detail: { tick: at, nodes } as TalonOpsRun["detail"],
			...overrides
		}
	}

	it("reads the node, the slope and each watermark in bytes on this disk", () => {
		const view = diskForecastView(evidence)
		expect(view?.watermarks.map(w => [w.key, w.pct, w.bytes, w.days])).toEqual([
			["low", 85, 850 * GIB, 7.5],
			["high", 90, 900 * GIB, 10],
			["flood_stage", 95, 950 * GIB, 12.5]
		])
		expect(diskForecastView({ used_gb: 1 })).toBeNull()
		expect(diskForecastView({ node: "n", thresholds_used_pct: {} })).toBeNull()
	})

	const DAILY = "45 4 * * *"
	const at = (iso: string) => Date.parse(iso)
	const disk = (used: number, total = 1000) => ({ "node-1": { used: used * GIB, total: total * GIB } })
	const shown = (points: { t: number; used: number }[]) => points.map(p => [new Date(p.t).toISOString(), p.used / GIB])

	it("builds Talon's series: per earlier UTC day the run nearest the scheduled time, today's the evidence's run", () => {
		const points = diskPoints(
			[
				run("2026-10-26T04:45:00Z", disk(700)), // now: the newest at or before last_seen
				run("2026-10-26T15:00:00Z", disk(705)), // after last_seen: not this finding's series
				run("2026-10-25T04:46:00Z", disk(680)), // the scheduled run (04:45) that day...
				run("2026-10-25T23:00:00Z", disk(685)), // ...not the latest
				run("2026-10-24T04:00:00Z", disk(660)), // 45 min early
				run("2026-10-24T05:30:00Z", disk(661)), // 45 min late: a tie goes to the earlier run
				run("2026-10-23T04:45:00Z", { "node-2": { used: 1, total: 2 } }), // not this node
				run("2026-10-22T04:45:00Z", { "node-1": { used: "650", total: 1000 * GIB } }), // malformed
				run("2026-10-21T04:45:00Z", disk(600), { job: "cluster_health" }), // another job
				run("2026-10-20T04:45:00Z", "not an object")
			],
			"node-1",
			{ lastSeen: at("2026-10-26T04:46:10Z"), schedule: DAILY }
		)
		expect(shown(points)).toEqual([
			["2026-10-24T04:00:00.000Z", 660],
			["2026-10-25T04:46:00.000Z", 680],
			["2026-10-26T04:45:00.000Z", 700]
		])
		expect(diskPoints(null, "node-1")).toEqual([])
	})

	it("uses the run's own time of day when the cron can't be read", () => {
		const runs = [run("2026-10-26T10:00:00Z", disk(700)), run("2026-10-25T04:45:00Z", disk(680)), run("2026-10-25T09:00:00Z", disk(690))]
		expect(shown(diskPoints(runs, "node-1", { schedule: "*/5 * * * *" }))).toEqual([
			["2026-10-25T09:00:00.000Z", 690],
			["2026-10-26T10:00:00.000Z", 700]
		])
		expect(shown(diskPoints(runs, "node-1", { schedule: DAILY }))[0]).toEqual(["2026-10-25T04:45:00.000Z", 680])
	})

	it("stops at a disk whose total differs by more than 0.5% (a resized or replaced disk)", () => {
		const runs = [
			run("2026-10-26T04:45:00Z", disk(700, 1000)),
			run("2026-10-25T04:45:00Z", disk(690, 1004)), // within 0.5%: the same disk
			run("2026-10-24T04:45:00Z", disk(400, 500)), // a smaller disk: the series stops here
			run("2026-10-23T04:45:00Z", disk(680, 1000)) // before it: never used again
		]
		expect(shown(diskPoints(runs, "node-1", { schedule: DAILY }))).toEqual([
			["2026-10-25T04:45:00.000Z", 690],
			["2026-10-26T04:45:00.000Z", 700]
		])
	})

	it("keeps the job's window and nothing before the evidence's series_since", () => {
		const runs = Array.from({ length: 20 }, (_, i) => run(new Date(at("2026-10-26T04:45:00Z") - i * 86400_000).toISOString(), disk(700 - i)))
		expect(diskPoints(runs, "node-1", { schedule: DAILY, windowDays: 14 })).toHaveLength(15)
		const since = diskPoints(runs, "node-1", { schedule: DAILY, seriesSince: at("2026-10-20T04:45:00.000Z") })
		expect(shown(since)[0]).toEqual(["2026-10-20T04:45:00.000Z", 694])
		expect(since).toHaveLength(7)
	})

	it("reads the schedule's time of day", () => {
		expect(scheduledTimeOfDay("45 4 * * *", 0)).toBe((4 * 60 + 45) * 60_000)
		expect(scheduledTimeOfDay("0 5 * * 1", 0)).toBe(5 * 3600_000)
		expect(scheduledTimeOfDay("5 * * * *", at("2026-10-26T10:30:00Z"))).toBe((10 * 60 + 5) * 60_000)
		expect(scheduledTimeOfDay("50 * * * *", at("2026-10-26T10:30:00Z"))).toBe((9 * 60 + 50) * 60_000)
		expect(scheduledTimeOfDay("*/5 * * * *", 0)).toBeNull()
		expect(scheduledTimeOfDay(null, 0)).toBeNull()
	})

	it("treats the high watermark as reached when the node is over it (days_to_high null)", () => {
		const over = must(diskForecastView({ ...evidence, days_to_high: null, over_high_watermark: true }))
		expect(over.watermarks.find(w => w.key === "high")?.days).toBe(0)
		const notForecast = must(diskForecastView({ ...evidence, days_to_high: null, over_high_watermark: false }))
		expect(notForecast.watermarks.find(w => w.key === "high")?.days).toBeNull()
		const flood = must(diskForecastView({ ...evidence, days_to_flood_stage: null, at_flood_stage: true }))
		expect(flood.watermarks.find(w => w.key === "flood_stage")?.days).toBe(0)
	})

	it("draws no chart with fewer than two points", () => {
		const view = must(diskForecastView(evidence))
		const one = diskPoints([run("2026-10-26T04:45:00Z", { "node-1": { used: 1, total: 2 } })], "node-1")
		expect(buildDiskChart(view, one, 30, { primary: "#A87400", warning: "#f90", error: "#f00" }, {})).toBeNull()
	})

	it("projects the slope to the horizon from the evidence at last_seen, and draws the watermarks", () => {
		const view = must(diskForecastView(evidence))
		const points = [
			{ t: Date.parse("2026-10-25T04:45:00Z"), used: 680 * GIB, total: 1000 * GIB },
			{ t: Date.parse("2026-10-26T04:45:00Z"), used: 698 * GIB, total: 1000 * GIB }
		]
		const lastSeen = Date.parse("2026-10-26T04:46:10Z")
		const colors = { primary: "#A87400", warning: "#f90", error: "#f00" }
		const chart = must(buildDiskChart(view, points, 30, colors, {}, { t: lastSeen, usedGb: 700 }))
		const series = chart.option.series as { name: string; data: number[][]; markLine?: { data: { yAxis: number }[] } }[]
		expect(series.map(s => s.name)).toEqual(["Used", "Projected"])
		expect(series[1].data).toEqual([
			[lastSeen, 700, 1000],
			[lastSeen + 30 * 86400_000, 700 + 20 * 30, 1000]
		])
		expect(series[0].markLine?.data.map(d => d.yAxis)).toEqual([850, 900, 950])
		expect(chart.summary).toContain("Low watermark at 85% (850.0 GB)")
		expect(chart.summary).toContain("20.00 GB/day")
		// Without an anchor, from the newest sample.
		const plain = must(buildDiskChart(view, points, 30, colors, {}))
		expect((plain.option.series as { data: number[][] }[])[1].data[0]).toEqual([points[1].t, 698, 1000])
	})

	it("gives each point its % of its own disk total", () => {
		const view = must(diskForecastView(evidence))
		const points = [
			{ t: Date.parse("2026-10-25T04:45:00Z"), used: 500 * GIB, total: 1002 * GIB },
			{ t: Date.parse("2026-10-26T04:45:00Z"), used: 700 * GIB, total: 1000 * GIB }
		]
		const chart = must(buildDiskChart(view, points, 30, { primary: "#A87400", warning: "#f90", error: "#f00" }, {}))
		const used = (chart.option.series as { data: number[][] }[])[0].data
		expect(used[0][2]).toBe(1002)
		const formatter = (chart.option.tooltip as { formatter: (p: unknown) => string }).formatter
		expect(formatter({ seriesName: "Used", value: used[0] })).toContain("(49.9%)")
		expect(formatter({ seriesName: "Used", value: used[1] })).toContain("(70%)")
	})

	it("projects to the job's horizon_days, else the furthest forecast watermark", () => {
		const view = must(diskForecastView(evidence))
		expect(projectionDays({ horizon_days: 30 }, view)).toBe(30)
		expect(projectionDays({ horizon_days: "30" }, view)).toBe(12.5)
		expect(projectionDays(null, must(diskForecastView({ ...evidence, days_to_low: null, days_to_high: null, days_to_flood_stage: null })))).toBeNull()
	})

	it("escapes every tooltip value, the node name included", () => {
		const html = diskTooltip(XSS, "sample", Date.parse("2026-10-26T04:45:00Z"), 700, 1000)
		expect(html).not.toContain("<img")
		expect(html).toContain("&lt;img src=x onerror=alert(1)&gt;")
		const view = must(diskForecastView({ ...evidence, node: XSS }))
		const points = [
			{ t: Date.parse("2026-10-25T04:45:00Z"), used: 680 * GIB, total: 1000 * GIB },
			{ t: Date.parse("2026-10-26T04:45:00Z"), used: 700 * GIB, total: 1000 * GIB }
		]
		const chart = must(buildDiskChart(view, points, 30, { primary: "#A87400", warning: "#f90", error: "#f00" }, {}))
		const formatter = (chart.option.tooltip as { formatter: (p: unknown) => string }).formatter
		const out = formatter({ seriesName: "Used", value: [points[1].t, 700] })
		expect(out).not.toContain("<img")
		expect(out).toContain("&lt;img")
		expect(formatter({ seriesName: "Used", value: "junk" })).toBe("")
		const container = document.createElement("div")
		container.innerHTML = out
		expect(container.querySelector("img")).toBeNull()
		expect(container.textContent).toContain(XSS)
	})
})

describe("which view", () => {
	it("picks a view by job only when the evidence parses", () => {
		expect(viewKind({ job: "quiet_endpoints", kind: "wazuh_quiet", evidence: { conditions: ["wazuh_quiet"] } })).toBe("quiet_endpoints")
		expect(viewKind({ job: "quiet_endpoints", kind: "wazuh_quiet", evidence: { conditions: "x" } })).toBeNull()
		expect(viewKind({ job: "cluster_health", kind: "cluster_status", evidence: { status: "red" } })).toBe("figures")
		expect(viewKind({ job: "cluster_health", kind: "cluster_status", evidence: { status: ["red"], x: 1 } })).toBeNull()
		expect(viewKind({ job: "new_job", kind: "x", evidence: { a: 1 } })).toBeNull()
		expect(viewKind({ job: "disk_forecast", kind: "disk_forecast", evidence: null })).toBeNull()
	})
})

describe("a finding's runs", () => {
	const base = { job: "quiet_endpoints", customer_code: "ACME", first_seen: "2026-10-20T06:00:00.123456+00:00" }
	function r(id: string, finished: string | null, overrides: Partial<TalonOpsRun> = {}) {
		return { id, job: "quiet_endpoints", customer_code: "ACME", finished_at: finished, started_at: null, tick: null, ...overrides } as TalonOpsRun
	}

	it("keeps the job's runs of its customer since first seen, newest first, at most 30", () => {
		const runs = [
			r("old", "2026-10-19T06:00:00Z"),
			r("first", "2026-10-20T06:00:01Z"),
			r("new", "2026-10-22T06:00:00Z"),
			r("other", "2026-10-22T06:00:00Z", { customer_code: "GLOBEX" }),
			r("job", "2026-10-22T06:00:00Z", { job: "agent_hygiene" }),
			r("untimed", null)
		]
		expect(findingRuns(runs, base).map(x => x.id)).toEqual(["new", "first"])
		const many = Array.from({ length: 40 }, (_, i) => r(`r${i}`, `2026-10-2${i % 7}T06:00:00Z`))
		expect(findingRuns(many, base)).toHaveLength(30)
		expect(findingRuns(runs, { ...base, customer_code: null })).toEqual([])
	})
})

describe("runs after a finding resolved", () => {
	it("marks a run that started after resolved_at, not the run that resolved it", () => {
		const finding = { resolved_at: "2026-10-24T06:00:30.123456+00:00" }
		expect(afterResolved({ started_at: "2026-10-24T06:00:00Z", tick: null }, finding)).toBe(false)
		expect(afterResolved({ started_at: "2026-10-25T06:00:00Z", tick: null }, finding)).toBe(true)
		expect(afterResolved({ started_at: null, tick: "2026-10-25T06:00:00Z" }, finding)).toBe(true)
		expect(afterResolved({ started_at: "2026-10-25T06:00:00Z", tick: null }, { resolved_at: null })).toBe(false)
	})
})
