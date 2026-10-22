import type { UnhealthyAgentPreview, UnhealthyAgentsDeletion, UnhealthyAgentsPreview } from "@/types/customers"
import { describe, expect, it, vi } from "vitest"
import {
	chunk,
	compactAge,
	confirmationMatches,
	DEFAULT_THRESHOLD,
	groupPreview,
	mergePreviews,
	needsCaution,
	needsTypedConfirmation,
	presetKey,
	resultsToReview,
	runChunkedDeletion,
	sameThreshold,
	thresholdFromListFilter,
	thresholdLabel,
	thresholdProblem,
	verdictText
} from "../unhealthyDelete"

/** Deleting unhealthy agents from the healthcheck lists (#1291): the dialog's pure rules. */

function agent(agentId: string, verdict: UnhealthyAgentPreview["verdict"]): UnhealthyAgentPreview {
	return {
		agent_id: agentId,
		verdict,
		hostname: `host-${agentId}`,
		label: null,
		os: null,
		last_seen: null,
		other_last_seen: null
	}
}

function answer(ids: string[], overrides: Partial<UnhealthyAgentsDeletion> = {}): UnhealthyAgentsDeletion {
	return {
		source: "wazuh",
		not_seen_for: { value: 30, unit: "days" },
		requested: ids.length,
		deleted: ids.length,
		skipped: 0,
		failed: 0,
		unconfirmed: 0,
		results: ids.map(id => ({ agent_id: id, hostname: null, outcome: "deleted", reason: null, unconfirmed: [] })),
		...overrides
	}
}

describe("the threshold", () => {
	it("is at least 24 hours, a whole number, at most ten years: the backend's own bounds", () => {
		expect(thresholdProblem({ value: 24, unit: "hours" })).toBeNull()
		expect(thresholdProblem({ value: 1, unit: "days" })).toBeNull()
		expect(thresholdProblem({ value: 3650, unit: "days" })).toBeNull()
		expect(thresholdProblem({ value: 23, unit: "hours" })).toMatch(/at least 24 hours/i)
		expect(thresholdProblem({ value: 3651, unit: "days" })).toMatch(/at most 3650 days/i)
		expect(thresholdProblem({ value: 0, unit: "days" })).toMatch(/whole number/i)
		expect(thresholdProblem({ value: 1.5, unit: "days" })).toMatch(/whole number/i)
		expect(thresholdProblem({ value: undefined, unit: "days" })).toMatch(/choose/i)
	})

	it("starts from the list's own filter, and from 30 days when that one cannot delete", () => {
		expect(thresholdFromListFilter({ time: 1, unit: "days" })).toEqual({ value: 1, unit: "days" })
		expect(thresholdFromListFilter({ time: 48, unit: "hours" })).toEqual({ value: 48, unit: "hours" })
		// Minutes round up to hours: a longer threshold deletes less, never more.
		expect(thresholdFromListFilter({ time: 1441, unit: "minutes" })).toEqual({ value: 25, unit: "hours" })
		expect(thresholdFromListFilter({ time: 2, unit: "hours" })).toEqual(DEFAULT_THRESHOLD)
		expect(thresholdFromListFilter({ time: 90, unit: "minutes" })).toEqual(DEFAULT_THRESHOLD)
		expect(thresholdFromListFilter({})).toEqual(DEFAULT_THRESHOLD)
	})

	it("names its preset by duration, so 24 hours and 1 day are the same one", () => {
		expect(presetKey({ value: 24, unit: "hours" })).toBe("24h")
		expect(presetKey({ value: 1, unit: "days" })).toBe("24h")
		expect(presetKey({ value: 168, unit: "hours" })).toBe("7d")
		expect(presetKey({ value: 30, unit: "days" })).toBe("30d")
		expect(presetKey({ value: 31, unit: "days" })).toBeNull()
		expect(presetKey({ value: 2, unit: "hours" })).toBeNull()
	})

	it("reads as written", () => {
		expect(thresholdLabel({ value: 1, unit: "days" })).toBe("1 day")
		expect(thresholdLabel({ value: 30, unit: "days" })).toBe("30 days")
		expect(thresholdLabel({ value: 1, unit: "hours" })).toBe("1 hour")
		expect(sameThreshold({ value: 1, unit: "days" }, { value: 1, unit: "days" })).toBe(true)
		// The same duration in other words is another request: the preview must be read again.
		expect(sameThreshold({ value: 1, unit: "days" }, { value: 24, unit: "hours" })).toBe(false)
		expect(sameThreshold(null, { value: 1, unit: "days" })).toBe(false)
	})
})

describe("confirming", () => {
	it("is cautious under a week, and asks for the count to be typed then or from ten agents", () => {
		expect(needsCaution({ value: 6, unit: "days" })).toBe(true)
		expect(needsCaution({ value: 167, unit: "hours" })).toBe(true)
		expect(needsCaution({ value: 7, unit: "days" })).toBe(false)

		expect(needsTypedConfirmation({ value: 30, unit: "days" }, 9)).toBe(false)
		expect(needsTypedConfirmation({ value: 30, unit: "days" }, 10)).toBe(true)
		expect(needsTypedConfirmation({ value: 1, unit: "days" }, 1)).toBe(true)
		expect(needsTypedConfirmation({ value: 1, unit: "days" }, 0)).toBe(false)
	})

	it("matches only the exact count", () => {
		expect(confirmationMatches(" 12 ", 12)).toBe(true)
		expect(confirmationMatches("12", 13)).toBe(false)
		expect(confirmationMatches("", 12)).toBe(false)
		expect(confirmationMatches("012", 12)).toBe(false)
	})
})

describe("the preview", () => {
	it("is read in chunks and merged back in request order", () => {
		expect(chunk(["a", "b", "c", "d", "e"], 2)).toEqual([["a", "b"], ["c", "d"], ["e"]])
		expect(chunk([], 10)).toEqual([])

		const part = (agents: UnhealthyAgentPreview[], deletable: number): UnhealthyAgentsPreview => ({
			source: "wazuh",
			not_seen_for: { value: 30, unit: "days" },
			cutoff: "2026-09-22T12:00:00",
			counts: {
				deletable,
				active_elsewhere: 0,
				seen_recently: agents.length - deletable,
				wazuh_manager: 0,
				not_found: 0
			},
			agents
		})
		const merged = mergePreviews([part([agent("1", "deletable")], 1), part([agent("2", "seen_recently")], 0)])
		expect(merged.agents.map(a => a.agent_id)).toEqual(["1", "2"])
		expect(merged.counts).toEqual({
			deletable: 1,
			active_elsewhere: 0,
			seen_recently: 1,
			wazuh_manager: 0,
			not_found: 0
		})
		expect(merged.cutoff).toBe("2026-09-22T12:00:00")
	})

	it("deletes the deletable, and the agents active elsewhere only when they are included", () => {
		const agents = [
			agent("1", "deletable"),
			agent("2", "active_elsewhere"),
			agent("3", "seen_recently"),
			agent("000", "wazuh_manager"),
			agent("4", "not_found")
		]
		const kept = groupPreview(agents, false)
		expect(kept.toDelete.map(a => a.agent_id)).toEqual(["1"])
		expect(kept.activeElsewhere.map(a => a.agent_id)).toEqual(["2"])
		expect(kept.kept.map(a => a.agent_id)).toEqual(["3", "000", "4"])

		const included = groupPreview(agents, true)
		expect(included.toDelete.map(a => a.agent_id)).toEqual(["1", "2"])
		expect(included.activeElsewhere).toEqual([])
	})

	it("says why an agent is kept, naming the other tool", () => {
		expect(verdictText("active_elsewhere", "wazuh").label).toBe("Seen by Velociraptor")
		expect(verdictText("active_elsewhere", "velociraptor").label).toBe("Seen by Wazuh")
		expect(verdictText("wazuh_manager", "wazuh").hint).toMatch(/never deleted/)
		expect(verdictText("not_found", "wazuh").hint).toMatch(/does not belong to this customer/)
	})
})

describe("the run", () => {
	it("sends one chunk at a time and adds up the answers", async () => {
		const sent: string[][] = []
		const progress: number[] = []
		const run = await runChunkedDeletion({
			ids: ["1", "2", "3", "4", "5"],
			chunkSize: 2,
			send: async ids => {
				sent.push(ids)
				return answer(ids, ids.includes("3") ? { deleted: 1, skipped: 1, unconfirmed: 1 } : {})
			},
			onChunk: (_, processed) => progress.push(processed)
		})
		expect(sent).toEqual([["1", "2"], ["3", "4"], ["5"]])
		expect(progress).toEqual([2, 4, 5])
		expect(run.totals).toEqual({ requested: 5, deleted: 4, unconfirmed: 1, skipped: 1, failed: 0, notSent: 0 })
		expect(run.stopped).toBe(false)
		expect(run.error).toBeNull()
	})

	it("is never concurrent: a chunk waits for the one before", async () => {
		let inFlight = 0
		let most = 0
		await runChunkedDeletion({
			ids: ["1", "2", "3"],
			chunkSize: 1,
			send: async ids => {
				inFlight += 1
				most = Math.max(most, inFlight)
				await new Promise(resolve => setTimeout(resolve, 5))
				inFlight -= 1
				return answer(ids)
			}
		})
		expect(most).toBe(1)
	})

	it("stops before the next chunk when asked, and counts what was not sent", async () => {
		let stop = false
		const send = vi.fn(async (ids: string[]) => {
			stop = true
			return answer(ids)
		})
		const run = await runChunkedDeletion({
			ids: ["1", "2", "3", "4", "5"],
			chunkSize: 2,
			send,
			shouldStop: () => stop
		})
		expect(send).toHaveBeenCalledTimes(1)
		expect(run.stopped).toBe(true)
		expect(run.totals).toMatchObject({ deleted: 2, notSent: 3 })
	})

	it("stops at the first failed request, keeping what was done", async () => {
		const failure = new Error("502")
		const send = vi
			.fn<(ids: string[]) => Promise<UnhealthyAgentsDeletion>>()
			.mockImplementationOnce(async ids => answer(ids))
			.mockRejectedValueOnce(failure)
		const run = await runChunkedDeletion({ ids: ["1", "2", "3", "4", "5"], chunkSize: 2, send })
		expect(send).toHaveBeenCalledTimes(2)
		expect(run.error).toBe(failure)
		expect(run.totals).toMatchObject({ deleted: 2, notSent: 3 })
	})

	it("lists failures first, then the unconfirmed, then the skipped; never a clean deletion", () => {
		const review = resultsToReview([
			{ agent_id: "1", hostname: null, outcome: "deleted", reason: null, unconfirmed: [] },
			{ agent_id: "2", hostname: null, outcome: "skipped", reason: "seen_recently", unconfirmed: [] },
			{ agent_id: "3", hostname: null, outcome: "deleted", reason: null, unconfirmed: ["velociraptor"] },
			{ agent_id: "4", hostname: null, outcome: "failed", reason: null, unconfirmed: [] }
		])
		expect(review.map(result => result.agent_id)).toEqual(["4", "3", "2"])
	})
})

describe("ages", () => {
	const now = Date.parse("2026-10-22T12:00:00Z")

	it("are compact, read from naive UTC", () => {
		expect(compactAge("2026-10-22T11:30:00", now)).toBe("<1 h")
		expect(compactAge("2026-10-22T07:00:00", now)).toBe("5 h")
		expect(compactAge("2026-10-20T12:00:00", now)).toBe("2 d")
		expect(compactAge("2026-09-12T12:00:00", now)).toBe("40 d")
		expect(compactAge("2023-10-22T12:00:00", now)).toBe("3 y")
		expect(compactAge("2026-10-22T11:30:00+00:00", now)).toBe("<1 h")
	})

	it("say never for no time and for the epoch the sync stores for Wazuh's Unknown", () => {
		expect(compactAge(null, now)).toBe("never")
		expect(compactAge("1970-01-01T00:00:00", now)).toBe("never")
		expect(compactAge("2026-10-23T12:00:00", now)).toBe("ahead")
	})
})
