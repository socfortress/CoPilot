/**
 * The Ops tab's pure helpers: which action a status allows (talon-analyst's transitions), the mute
 * window (future, at most 90 days) and its presets, the evidence as rows, labels, the jobs' schedules in
 * words and their summary, what Run now found, and what a failure shows.
 */
import type { TalonOpsRun } from "@/types/talonOps"
import { describe, expect, it } from "vitest"
import {
	byWorst,
	canAcknowledge,
	canMute,
	canReopen,
	currentRuns,
	customerText,
	evidenceRows,
	expectedRuns,
	freshRuns,
	hiddenPlatformJob,
	humanSchedule,
	isTransient,
	isValidMuteUntil,
	JOB_LABELS,
	jobLabel,
	jobRuns,
	jobsSummary,
	jobState,
	KIND_LABELS,
	kindLabel,
	lastFinished,
	MUTE_PRESETS,
	muteUntilIn,
	OLD_TALON_OPS_TEXT,
	problemState,
	runResult,
	runsDone,
	severityInfo,
	statusTone,
	triggerTick,
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
	it("are 1, 7 and 30 calendar days, each inside the 90-day window", () => {
		expect([...MUTE_PRESETS]).toEqual([1, 7, 30])
		for (const days of MUTE_PRESETS) {
			const expected = new Date(now)
			expected.setDate(expected.getDate() + days)
			expect(muteUntilIn(days, now)).toBe(expected.getTime())
			expect(new Date(muteUntilIn(days, now)).getHours()).toBe(new Date(now).getHours())
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
		["5 * * * *", "Hourly at :05 UTC"],
		["15 * * * *", "Hourly at :15 UTC"],
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

function job(
	name: string,
	runs: TalonOpsRun[],
	enabled = true,
	extra: { scope?: "platform" | "customer"; schedule_status?: string | null } = {}
) {
	return {
		name,
		enabled,
		scope: extra.scope ?? ("customer" as const),
		schedule_status: extra.schedule_status ?? "ACTIVE",
		last_run: runs[0] ?? null,
		last_runs: runs
	}
}

const OLD_TICK = "2026-10-20T05:00:00+00:00"

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

	it("keeps only the newest tick's runs: an old skipped row and a customer gone from scope drop out", () => {
		const acme = run("ACME", "ok")
		const beta = run("BETA", "ok")
		const oldSkip = run(null, "skipped", { tick: OLD_TICK, finished_at: OLD_TICK })
		const gone = run("GONE", "failed", { tick: OLD_TICK, finished_at: OLD_TICK })
		const runs = [acme, beta, oldSkip, gone]
		expect(currentRuns({ last_run: acme, last_runs: runs })).toEqual([acme, beta])
		expect(expectedRuns({ scope: "customer", last_run: acme, last_runs: runs })).toBe(2)
		expect(jobsSummary([job("quiet_endpoints", runs)])).toEqual({ tone: "ok", text: "1 enabled · last runs ok" })
	})

	describe("a tick still in progress", () => {
		// Units queue behind TALON_OPS_CONCURRENCY: 4 of 10 customers have run at 07:50 so far.
		const NOW_TICK = "2026-10-24T07:50:00+00:00"
		const PREV_TICK = "2026-10-23T07:50:00+00:00"
		const now = Date.parse("2026-10-24T08:00:00Z")
		const customers = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
		const lastRuns = (failedE = true) =>
			customers.map((c, i) =>
				i < 4
					? run(c, "ok", { id: `now-${c}`, tick: NOW_TICK, finished_at: "2026-10-24T07:55:00Z" })
					: run(c, c === "E" && failedE ? "failed" : "ok", {
							id: `prev-${c}`,
							tick: PREV_TICK,
							finished_at: PREV_TICK
						})
			)
		const storage = (runs: TalonOpsRun[]) => ({ ...job("storage_usage", runs), scope: "customer" as const })

		it("counts every customer of both ticks, a customer not run yet with its previous run", () => {
			const state = jobState(storage(lastRuns()), now)
			expect(state.running).toEqual({ done: 4, total: 10 })
			expect(state.runs).toHaveLength(10)
			expect(worstStatus(state.runs)).toBe("failed")
			expect(expectedRuns(storage(lastRuns()), now)).toBe(10)
		})

		it("hides nothing in the summary: running, never ok, and yesterday's failure stays", () => {
			expect(jobsSummary([storage(lastRuns())], true, now)).toEqual({
				tone: "error",
				text: "1 failed (storage_usage) · 1 running (storage_usage 4 of 10)"
			})
			expect(jobsSummary([storage(lastRuns(false))], true, now)).toEqual({
				tone: "ok",
				text: "1 enabled · 1 running (storage_usage 4 of 10)"
			})
		})

		it("is settled once its runs are older than the unit timeout: the missing customers left scope", () => {
			const later = Date.parse("2026-10-24T08:26:00Z")
			const state = jobState(storage(lastRuns()), later)
			expect(state.running).toBeNull()
			expect(state.runs.map(r => r.customer_code)).toEqual(["A", "B", "C", "D"])
			expect(jobsSummary([storage(lastRuns())], true, later).text).toBe("1 enabled · last runs ok")
		})

		it("counts a customer missing from the last tick", () => {
			// NEW was added since the previous tick: it is in the newest one only. BETA hasn't run yet.
			const acme = run("ACME", "ok", { tick: NOW_TICK, finished_at: "2026-10-24T07:55:00Z" })
			const added = run("NEW", "partial", { tick: NOW_TICK, finished_at: "2026-10-24T07:56:00Z" })
			const beta = run("BETA", "ok", { tick: PREV_TICK, finished_at: PREV_TICK })
			const inProgress = jobState({ last_run: added, last_runs: [added, acme, beta] }, now)
			expect(inProgress.running).toEqual({ done: 2, total: 3 })
			expect(expectedRuns({ scope: "customer", last_run: added, last_runs: [added, acme, beta] }, now)).toBe(3)
			// Settled: BETA ran too, NEW counts though the previous tick never had it.
			const betaNow = run("BETA", "ok", { tick: NOW_TICK, finished_at: "2026-10-24T07:57:00Z" })
			const settled = jobState({ last_run: added, last_runs: [added, acme, betaNow] }, now)
			expect(settled.running).toBeNull()
			expect(settled.runs.map(r => r.customer_code)).toEqual(["NEW", "ACME", "BETA"])
			expect(expectedRuns({ scope: "customer", last_run: added, last_runs: [added, acme, betaNow] }, now)).toBe(3)
		})

		it("isn't started by an old skipped run without a customer", () => {
			const acme = run("ACME", "ok", { tick: NOW_TICK, finished_at: "2026-10-24T07:55:00Z" })
			const skip = run(null, "skipped", { tick: PREV_TICK, finished_at: PREV_TICK })
			const state = jobState({ last_run: acme, last_runs: [acme, skip] }, now)
			expect(state.running).toBeNull()
			expect(state.runs).toEqual([acme])
		})
	})

	it("a tick in another notation is the same tick", () => {
		const a = run("A", "ok", { tick: "2026-10-24T05:00:00Z" })
		const b = run("B", "ok", { tick: "2026-10-24T05:00:00.000000+00:00" })
		expect(currentRuns({ last_run: a, last_runs: [a, b] })).toEqual([a, b])
	})

	it("sorts worst first, and finds the newest finish", () => {
		const ok = run("A", "ok", { finished_at: "2026-10-24T05:00:09Z" })
		const partial = run("B", "partial", { finished_at: "2026-10-24T05:00:02Z" })
		const failed = run("C", "failed", { finished_at: "2026-10-24T05:00:05Z" })
		expect(byWorst([ok, partial, failed]).map(r => r.status)).toEqual(["failed", "partial", "ok"])
		expect(lastFinished([partial, ok, failed])).toBe("2026-10-24T05:00:09Z")
		expect(lastFinished([])).toBeNull()
	})

	it("hides a platform job's runs from a non-admin", () => {
		expect(hiddenPlatformJob({ scope: "platform" }, false)).toBe(true)
		expect(hiddenPlatformJob({ scope: "platform" }, true)).toBe(false)
		expect(hiddenPlatformJob({ scope: "customer" }, false)).toBe(false)
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

	it("keeps 'not run yet' beside the others, and a schedule that isn't ACTIVE is a warning", () => {
		const jobs = [
			job("quiet_endpoints", [run("A", "partial")]),
			job("storage_usage", [run("A", "ok")], true, { schedule_status: "PAUSED" }),
			job("agent_hygiene", [])
		]
		expect(jobsSummary(jobs)).toEqual({
			tone: "warning",
			text: "1 partial (quiet_endpoints) · 1 schedule paused (storage_usage) · 1 not run yet"
		})
		expect(jobsSummary([job("storage_usage", [run("A", "ok")], true, { schedule_status: "PAUSED" })])).toEqual({
			tone: "warning",
			text: "1 schedule paused (storage_usage)"
		})
		// A disabled job's schedule doesn't count.
		expect(jobsSummary([job("a", [run("A", "ok")]), job("b", [], false, { schedule_status: "PAUSED" })]).text).toBe(
			"1 enabled · last runs ok"
		)
	})

	it("leaves a platform job out for a non-admin", () => {
		const jobs = [job("quiet_endpoints", [run("A", "ok")]), job("cluster_health", [], true, { scope: "platform" })]
		expect(jobsSummary(jobs, false)).toEqual({ tone: "ok", text: "1 enabled · last runs ok" })
		expect(jobsSummary(jobs, true).text).toBe("2 enabled · last runs ok · 1 not run yet")
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
	const TICK = "2026-10-24T06:00:00.123456+00:00"
	const WORKFLOW = `sched-talon-ops:quiet_endpoints-trigger-${TICK}`
	const tick = Date.parse("2026-10-24T06:00:00.123Z")
	const old = run("A", "ok", { id: "old", tick: "2026-10-24T05:00:00+00:00", finished_at: "2026-10-24T05:00:00Z" })
	const fresh = run("A", "ok", {
		id: `quiet_endpoints:A:${TICK}`,
		tick: TICK,
		triggered_by: "manual",
		finished_at: "2026-10-24T06:00:30Z",
		new: 2,
		updated: 1,
		resolved: 3
	})
	const unfinished = run("B", "ok", { id: "running", tick: TICK, triggered_by: "manual", finished_at: null })
	// A scheduled run, and another admin's run now, finishing during the watch.
	const scheduled = run("A", "ok", {
		id: "sched",
		tick: "2026-10-24T06:05:00+00:00",
		finished_at: "2026-10-24T06:05:10Z"
	})
	const otherClick = run("A", "ok", {
		id: "other",
		tick: "2026-10-24T05:59:00+00:00",
		triggered_by: "manual",
		finished_at: "2026-10-24T06:00:40Z"
	})

	it("reads the tick from Talon's workflow id", () => {
		expect(triggerTick(WORKFLOW)).toBe(tick)
		expect(triggerTick("sched-talon-ops:cluster_health-trigger-2026-10-24T06:00:00Z")).toBe(
			Date.parse("2026-10-24T06:00:00Z")
		)
		expect(triggerTick("w")).toBeNull()
		expect(triggerTick(null)).toBeNull()
		expect(triggerTick("sched-talon-ops:x-trigger-yesterday")).toBeNull()
	})

	it("is this click's manual runs of its tick: never a scheduled run or another click", () => {
		expect(freshRuns([scheduled, otherClick, fresh, old, unfinished], tick, null)).toEqual([fresh])
		expect(freshRuns([{ ...fresh, triggered_by: "schedule" }], tick, null)).toEqual([])
		// Another admin's click in the same second.
		const sameSecond = { ...fresh, id: "same-second", tick: "2026-10-24T06:00:00.623456+00:00" }
		expect(freshRuns([sameSecond, fresh], tick, null)).toEqual([fresh])
	})

	it("tells apart two clicks 400 ms apart, and matches a tick to the millisecond", () => {
		const first = run("A", "ok", { id: "first", tick: "2026-10-24T06:00:02.100000+00:00", triggered_by: "manual" })
		const second = run("A", "ok", {
			id: "second",
			tick: "2026-10-24T06:00:02.500000+00:00",
			triggered_by: "manual"
		})
		const firstTick = triggerTick("sched-talon-ops:storage_usage-trigger-2026-10-24T06:00:02.100000+00:00")
		const secondTick = triggerTick("sched-talon-ops:storage_usage-trigger-2026-10-24T06:00:02.500000+00:00")
		expect(freshRuns([second, first], firstTick, null)).toEqual([first])
		expect(freshRuns([second, first], secondTick, null)).toEqual([second])
		// Microseconds are cut, never rounded, on both sides.
		const edge = run("A", "ok", { id: "edge", tick: "2026-10-24T06:00:02.100999+00:00", triggered_by: "manual" })
		expect(freshRuns([edge], triggerTick("x-trigger-2026-10-24T06:00:02.100999+00:00"), null)).toEqual([edge])
		expect(freshRuns([edge], triggerTick("x-trigger-2026-10-24T06:00:02.104000+00:00"), null)).toEqual([])
	})

	it("without a workflow id: the manual runs Talon didn't have before the click, of the newest tick", () => {
		const before = new Set(["old", "other"])
		expect(freshRuns([scheduled, fresh, old, otherClick, unfinished], null, before)).toEqual([fresh])
	})

	it("with neither, finds nothing: the browser's clock is never used", () => {
		expect(freshRuns([fresh, scheduled], null, null)).toEqual([])
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

	it("retries only a transient failure", () => {
		expect(isTransient({ status: null })).toBe(true)
		expect(isTransient({ status: 502 })).toBe(true)
		expect(isTransient({ status: 503 })).toBe(true)
		expect(isTransient({ status: 429 })).toBe(true)
		expect(isTransient({ status: 403 })).toBe(false)
		expect(isTransient({ status: 404 })).toBe(false)
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
