/**
 * The Ops tab's pure helpers: which action a status allows (talon-analyst's transitions), the mute
 * window (future, at most 90 days) and its presets, the evidence as rows, labels, the jobs' schedules in
 * words and their summary, what Run now found, and what a failure shows.
 */
import type { TalonOpsRun } from "@/types/talonOps"
import { describe, expect, it } from "vitest"
import {
	canAcknowledge,
	canMute,
	canReopen,
	customerText,
	evidenceRows,
	expectedRuns,
	freshRuns,
	humanSchedule,
	isValidMuteUntil,
	JOB_LABELS,
	jobLabel,
	jobRuns,
	jobsSummary,
	KIND_LABELS,
	kindLabel,
	MUTE_PRESETS,
	muteUntilIn,
	OLD_TALON_OPS_TEXT,
	problemState,
	runResult,
	runsDone,
	severityInfo,
	statusTone,
	V2_OFF_TEXT,
	worstStatus
} from "../ops"

const DAY = 24 * 60 * 60 * 1000

describe("actions by status", () => {
	it.each([
		["open", true, true, false],
		["acknowledged", false, true, true],
		["muted", true, true, true],
		["resolved", false, false, false]
	] as const)("%s: acknowledge %s, mute %s, reopen %s", (status, ack, mute, reopen) => {
		expect(canAcknowledge(status)).toBe(ack)
		expect(canMute(status)).toBe(mute)
		expect(canReopen(status)).toBe(reopen)
	})
})

describe("the mute window", () => {
	const now = Date.UTC(2026, 9, 24, 12)
	it("is in the future and at most 90 days away", () => {
		expect(isValidMuteUntil(now + DAY, now)).toBe(true)
		expect(isValidMuteUntil(now + 90 * DAY, now)).toBe(true)
		expect(isValidMuteUntil(now + 90 * DAY + 1, now)).toBe(false)
		expect(isValidMuteUntil(now, now)).toBe(false)
		expect(isValidMuteUntil(now - 1, now)).toBe(false)
		expect(isValidMuteUntil(null, now)).toBe(false)
		expect(isValidMuteUntil(Number.NaN, now)).toBe(false)
	})
})

describe("mute presets", () => {
	const now = Date.UTC(2026, 9, 24, 12)
	it("are 1, 7 and 30 days, each inside the 90-day window", () => {
		expect([...MUTE_PRESETS]).toEqual([1, 7, 30])
		for (const days of MUTE_PRESETS) {
			expect(muteUntilIn(days, now)).toBe(now + days * DAY)
			expect(isValidMuteUntil(muteUntilIn(days, now), now)).toBe(true)
		}
		expect(isValidMuteUntil(muteUntilIn(91, now), now)).toBe(false)
	})
})

describe("evidence rows", () => {
	it("keeps the job's order, shows scalars and lists of scalars as text, and objects as JSON", () => {
		const rows = evidenceRows({
			agent_id: "017",
			critical_asset: false,
			wazuh_days_quiet: 5.1,
			velociraptor_id: null,
			conditions: ["wazuh_quiet", "velociraptor_quiet"],
			same_hour_last_4_weeks: [],
			nested: { a: 1 }
		})
		expect(rows.map(r => r.key)).toEqual([
			"agent_id",
			"critical_asset",
			"wazuh_days_quiet",
			"velociraptor_id",
			"conditions",
			"same_hour_last_4_weeks",
			"nested"
		])
		expect(rows.map(r => r.text)).toEqual([
			"017",
			"no",
			"5.1",
			"—",
			"wazuh_quiet, velociraptor_quiet",
			"none",
			null
		])
		expect(rows[6].json).toBe(JSON.stringify({ a: 1 }, null, 2))
	})

	it("is empty without evidence", () => {
		expect(evidenceRows(null)).toEqual([])
	})
})

describe("labels", () => {
	it("names jobs, kinds, customers and severities", () => {
		expect(jobLabel("quiet_endpoints")).toBe("Endpoints gone quiet")
		expect(jobLabel("quiet_endpoints", { quiet_endpoints: "Quiet agents" })).toBe("Quiet agents")
		expect(jobLabel("new_job")).toBe("new_job")
		expect(kindLabel("wazuh_quiet")).toBe("Wazuh quiet")
		expect(kindLabel("some_new_kind")).toBe("some new kind")
		expect(customerText(null)).toBe("Platform")
		expect(customerText("ACME")).toBe("ACME")
		expect(severityInfo("high")).toMatchObject({ label: "High", tag: "error" })
		expect(severityInfo("info")).toMatchObject({ label: "Info", tag: "default" })
	})
})

describe("every job and kind has a label", () => {
	it("names the nine jobs", () => {
		expect(Object.keys(JOB_LABELS).sort()).toEqual(
			[
				"agent_hygiene",
				"cluster_health",
				"disk_forecast",
				"exclusion_candidates",
				"mapping_drift",
				"noisy_events",
				"quiet_endpoints",
				"silent_log_sources",
				"storage_usage"
			].sort()
		)
		expect(jobLabel("cluster_health")).toBe("Indexer cluster health")
		expect(jobLabel("mapping_drift")).toBe("Index mapping drift")
	})

	// The kinds each job module emits (talon-analyst `src/talon/ops/jobs/*.py`, SPEC §5.7).
	it.each([
		["wazuh_version", "Wazuh agent version"],
		["velociraptor_missing", "No Velociraptor client"],
		["velociraptor_version", "Velociraptor version"],
		["cluster_status", "Cluster status"],
		["unassigned_shards", "Unassigned shards"],
		["disk_watermark", "Disk watermark"],
		["shard_capacity", "Shard capacity"],
		["ism_failure", "ISM failure"],
		["node_count_drop", "Data nodes lost"],
		["disk_forecast", "Disk forecast"],
		["field_limit", "Field limit"],
		["type_conflict", "Type conflict"],
		["field_growth", "Field growth"],
		["talon_fields", "Talon's fields"],
		["ingest_growth", "Ingest growth"],
		["large_footprint", "Large footprint"],
		["tuning_candidate", "Tuning candidate"],
		["exclusion_candidate", "Exclusion candidate"],
		["silent", "Silent"],
		["never_connected", "Never connected"]
	])("%s: %s", (kind, label) => {
		expect(KIND_LABELS[kind]).toBe(label)
		expect(kindLabel(kind)).toBe(label)
	})

	it("humanises a kind it doesn't know", () => {
		expect(kindLabel("brand_new_kind")).toBe("brand new kind")
		expect(kindLabel(null)).toBe("Unknown")
	})
})

describe("schedules in words", () => {
	it.each([
		["30 5 * * *", "Daily 05:30 UTC"],
		["0 6 * * *", "Daily 06:00 UTC"],
		["5 * * * *", "Hourly at :05"],
		["15 * * * *", "Hourly at :15"],
		["0 5 * * 1", "Mondays 05:00 UTC"],
		["0 5 * * 2", "Tuesdays 05:00 UTC"],
		["0 5 * * 0", "Sundays 05:00 UTC"],
		["0 5 * * 7", "Sundays 05:00 UTC"],
		["  45 4 * * *  ", "Daily 04:45 UTC"]
	])("%s: %s", (cron, words) => {
		expect(humanSchedule(cron)).toBe(words)
	})

	it.each([
		"*/15 * * * *",
		"0 */6 * * *",
		"0 5 1 * *",
		"0 5 * 1 *",
		"0 5 * * 1-5",
		"0 5 * * MON",
		"0 5,17 * * *",
		"60 5 * * *",
		"0 24 * * *",
		"5 * * * 1",
		"0 5 * *",
		"@daily"
	])("%s: shown as it is", cron => {
		expect(humanSchedule(cron)).toBe(cron)
	})

	it("says — without a schedule", () => {
		expect(humanSchedule(null)).toBe("—")
		expect(humanSchedule("")).toBe("—")
	})
})

function run(customer: string | null, status: string, overrides: Partial<TalonOpsRun> = {}): TalonOpsRun {
	return {
		id: `job:${customer ?? "-"}:${status}`,
		job: "job",
		job_version: 1,
		customer_code: customer,
		tick: "2026-10-24T05:00:00Z",
		triggered_by: "schedule",
		status,
		collected: true,
		explained: null,
		candidates: 0,
		new: 0,
		updated: 0,
		resolved: 0,
		error: null,
		cost_usd: "0",
		duration_ms: 10,
		started_at: "2026-10-24T05:00:00Z",
		finished_at: "2026-10-24T05:00:01Z",
		...overrides
	}
}

function job(name: string, runs: TalonOpsRun[], enabled = true) {
	return { name, enabled, last_run: runs[0] ?? null, last_runs: runs }
}

describe("last runs", () => {
	it("takes the worst status across the customers' newest runs", () => {
		expect(worstStatus([run("A", "ok"), run("B", "skipped"), run("C", "ok")])).toBe("skipped")
		expect(worstStatus([run("A", "skipped"), run("B", "partial")])).toBe("partial")
		expect(worstStatus([run("A", "partial"), run("B", "failed"), run("C", "ok")])).toBe("failed")
		expect(worstStatus([run("A", "ok"), run("B", "something_new")])).toBe("something_new")
		expect(worstStatus([])).toBeNull()
		expect(statusTone("failed")).toBe("error")
		expect(statusTone("partial")).toBe("warning")
		expect(statusTone("skipped")).toBe("warning")
		expect(statusTone("ok")).toBe("ok")
	})

	it("falls back to the newest run when Talon sends no per-customer runs", () => {
		const only = run("A", "ok")
		expect(jobRuns({ last_run: only, last_runs: [] })).toEqual([only])
		expect(jobRuns({ last_run: null, last_runs: [] })).toEqual([])
	})
})

describe("the jobs' summary", () => {
	it("all fine: the enabled count and 'last runs ok'", () => {
		const jobs = Array.from({ length: 9 }, (_, i) => job(`job_${i}`, [run("A", "ok"), run("B", "ok")]))
		expect(jobsSummary(jobs)).toEqual({ tone: "ok", text: "9 enabled · last runs ok" })
		expect(jobsSummary([...jobs, job("never", [])])).toEqual({
			tone: "ok",
			text: "10 enabled · last runs ok · 1 not run yet"
		})
	})

	it("partial or skipped: amber, naming the jobs, a disabled job left out", () => {
		const jobs = [
			job("quiet_endpoints", [run("A", "ok")]),
			job("mapping_drift", [run("A", "ok"), run("B", "partial")]),
			job("disk_forecast", [run(null, "skipped")]),
			job("old_job", [run("A", "failed")], false)
		]
		expect(jobsSummary(jobs)).toEqual({
			tone: "warning",
			text: "1 partial (mapping_drift) · 1 skipped (disk_forecast)"
		})
	})

	it("a failed run: red, worst first", () => {
		const jobs = [
			job("storage_usage", [run("A", "skipped")]),
			job("noisy_events", [run("A", "skipped")]),
			job("cluster_health", [run(null, "failed")])
		]
		expect(jobsSummary(jobs)).toEqual({
			tone: "error",
			text: "1 failed (cluster_health) · 2 skipped (storage_usage, noisy_events)"
		})
	})

	it("no jobs, or none enabled", () => {
		expect(jobsSummary([]).text).toBe("No ops jobs")
		expect(jobsSummary([job("a", [], false)]).text).toBe("1 job, none enabled")
		expect(jobsSummary([job("a", [], false), job("b", [], false)]).text).toBe("2 jobs, none enabled")
	})
})

describe("what run now found", () => {
	const clickedAt = Date.parse("2026-10-24T06:00:00Z")
	const old = run("A", "ok", { id: "old", finished_at: "2026-10-24T05:00:00Z" })
	const fresh = run("A", "ok", { id: "new", finished_at: "2026-10-24T06:00:30Z", new: 2, updated: 1, resolved: 3 })
	const unfinished = run("B", "ok", { id: "running", finished_at: null })

	it("is the finished runs Talon didn't have at the click", () => {
		expect(freshRuns([fresh, old, unfinished], new Set(["old"]), clickedAt)).toEqual([fresh])
		// Even when this browser's clock is ahead of Talon's.
		const early = { ...fresh, finished_at: "2026-10-24T05:59:00Z" }
		expect(freshRuns([early, old], new Set(["old"]), clickedAt)).toEqual([early])
	})

	it("without that list, is the runs that finished after the click", () => {
		expect(freshRuns([fresh, old, unfinished], null, clickedAt)).toEqual([fresh])
	})

	it("is done with one run per customer, or one without a customer", () => {
		expect(expectedRuns({ scope: "customer", last_run: null, last_runs: [run("A", "ok"), run("B", "ok")] })).toBe(2)
		expect(expectedRuns({ scope: "customer", last_run: null, last_runs: [] })).toBe(1)
		expect(expectedRuns({ scope: "platform", last_run: null, last_runs: [] })).toBe(1)
		expect(runsDone([run("A", "ok")], 2)).toBe(false)
		expect(runsDone([run("A", "ok"), run("B", "ok")], 2)).toBe(true)
		expect(runsDone([run(null, "skipped")], 2)).toBe(true)
	})

	it("says what the runs found", () => {
		expect(runResult("Endpoints gone quiet", [fresh], 1, true, false)).toEqual({
			type: "success",
			text: "Endpoints gone quiet finished: 2 new, 1 updated, 3 resolved."
		})
		expect(runResult("Storage", [{ ...fresh, status: "partial" }], 1, true, false)).toEqual({
			type: "warning",
			text: "Storage finished (partial): 2 new, 1 updated, 3 resolved."
		})
		expect(runResult("Storage", [fresh], 3, false, false).text).toBe(
			"Storage: 2 new, 1 updated, 3 resolved so far (1 of 3 customers); still running."
		)
		expect(runResult("Storage", [fresh], 3, false, true).text).toBe(
			"Storage: 2 new, 1 updated, 3 resolved so far (1 of 3 customers); the rest are still running; refresh later."
		)
		expect(runResult("Storage", [], 1, false, true)).toEqual({
			type: "info",
			text: "Storage is still running; refresh later."
		})
	})
})

describe("problems", () => {
	it("tells v2 off and an old Talon apart from a failure", () => {
		expect(problemState({ status: 404, code: "v2_off", detail: "x" })).toMatchObject({
			kind: "v2_off",
			text: V2_OFF_TEXT
		})
		expect(problemState({ status: 404, code: "unsupported", detail: "x" })).toMatchObject({
			kind: "unsupported",
			text: OLD_TALON_OPS_TEXT
		})
		expect(problemState({ status: 502, code: "unavailable", detail: "Talon could not be reached" })).toMatchObject({
			kind: "error",
			text: "Talon could not be reached"
		})
		expect(problemState(null)).toBeNull()
	})
})
