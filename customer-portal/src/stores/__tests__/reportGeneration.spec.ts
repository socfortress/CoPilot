import type { IncidentCustomerReportStatus } from "@/types/reports"
import { flushPromises } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { POLL_TIMEOUT_MS, pollDelay, STATUS_BATCH, useReportGenerationStore } from "../reportGeneration"

const getReportStatuses = vi.hoisted(() => vi.fn())
const prepend = vi.hoisted(() => vi.fn())
vi.mock("@/api", () => ({ default: { reports: { getReportStatuses } } }))
vi.mock("@/composables/common/useNotifications", () => ({ useNotifications: () => ({ prepend }) }))

function status(
	id: number,
	value: IncidentCustomerReportStatus["status"],
	extra: Partial<IncidentCustomerReportStatus> = {}
) {
	return { id, report_name: `r${id}`, file_name: `r${id}.pdf`, status: value, started_at: "", ...extra }
}

function answer(reports: IncidentCustomerReportStatus[], missing: number[] = []) {
	return Promise.resolve({ data: { success: true, message: "ok", reports, missing } })
}

/** Lets the next scheduled poll run and its answer land. */
async function tick(ms: number) {
	await vi.advanceTimersByTimeAsync(ms)
	await flushPromises()
}

describe("report generation poller (#1263)", () => {
	beforeEach(() => {
		vi.useFakeTimers()
		vi.setSystemTime(new Date("2026-10-16T10:00:00Z"))
		setActivePinia(createPinia())
		getReportStatuses.mockReset()
		prepend.mockReset()
	})
	afterEach(() => {
		useReportGenerationStore().reset()
		vi.useRealTimers()
	})

	it("asks often at first, then less and less", () => {
		expect([0, 59_999, 60_000, 299_999, 300_000, 3_600_000].map(pollDelay)).toEqual([
			3_000, 3_000, 10_000, 10_000, 30_000, 30_000
		])
	})

	it("asks about the pending reports only, a few seconds after one is queued", async () => {
		getReportStatuses.mockImplementation(() => answer([status(5, "processing")]))
		const store = useReportGenerationStore()
		store.track({ id: 5, name: "Weekly" })
		expect(getReportStatuses).not.toHaveBeenCalled()

		await tick(3_000)
		expect(getReportStatuses).toHaveBeenCalledWith([5])
		expect(store.isPending(5)).toBe(true)
	})

	it("says a report is ready, with a Download that leads straight to the file", async () => {
		getReportStatuses.mockImplementation(() => answer([status(5, "completed")]))
		const store = useReportGenerationStore()
		store.track({ id: 5, name: "Weekly" })
		await tick(3_000)

		expect(prepend).toHaveBeenCalledTimes(1)
		const [item, options] = prepend.mock.calls[0]!
		expect(item).toMatchObject({
			id: "report-5",
			type: "success",
			title: "Report ready",
			actionRoute: { name: "ReportsList", query: { download: "5" } },
			actionTitle: "Download"
		})
		expect(options).toEqual({ sendNotify: true })
		expect(store.pending).toEqual([])
		expect(store.lastResolvedAt).toBeGreaterThan(0)

		// Nothing left to wait for: no more requests.
		await tick(60_000)
		expect(getReportStatuses).toHaveBeenCalledTimes(1)
	})

	it("says a report failed, with the error the backend lets the customer read", async () => {
		getReportStatuses.mockImplementation(() =>
			answer([status(5, "failed", { error_message: "The report could not be generated." })])
		)
		const store = useReportGenerationStore()
		store.track({ id: 5, name: "Weekly" })
		await tick(3_000)
		expect(prepend.mock.calls[0]![0]).toMatchObject({
			type: "error",
			title: "Report failed",
			description: "The report could not be generated.",
			actionRoute: { name: "ReportsList" }
		})
	})

	it("drops a report that is gone (deleted, or no longer the user's) without a word", async () => {
		getReportStatuses.mockImplementation(() => answer([], [5]))
		const store = useReportGenerationStore()
		store.track({ id: 5, name: "Weekly" })
		await tick(3_000)
		expect(prepend).not.toHaveBeenCalled()
		expect(store.pending).toEqual([])
	})

	it("slows down as a report keeps running, and gives up with a word after the deadline", async () => {
		getReportStatuses.mockImplementation(() => answer([status(5, "processing")]))
		const store = useReportGenerationStore()
		store.track({ id: 5, name: "Weekly" })

		await tick(3_000)
		await tick(57_000) // the rest of the first minute: every 3 s
		const firstMinute = getReportStatuses.mock.calls.length
		expect(firstMinute).toBe(20)
		await tick(60_000) // then every 10 s
		expect(getReportStatuses.mock.calls.length - firstMinute).toBe(6)

		await tick(POLL_TIMEOUT_MS)
		expect(prepend.mock.calls.at(-1)![0]).toMatchObject({ type: "warning", title: "Report still running" })
		expect(store.pending).toEqual([])
	})

	it("never sends a second request while one is still out", async () => {
		let answerNow: (value: unknown) => void = () => {}
		getReportStatuses.mockImplementation(() => new Promise(resolve => (answerNow = resolve)))
		const store = useReportGenerationStore()
		store.track({ id: 5, name: "Weekly" })
		await tick(3_000)
		await tick(30_000)
		store.poll()
		expect(getReportStatuses).toHaveBeenCalledTimes(1)

		getReportStatuses.mockImplementation(() => answer([status(5, "processing")]))
		answerNow({ data: { success: true, message: "ok", reports: [status(5, "processing")], missing: [] } })
		await flushPromises()
		await tick(3_000)
		expect(getReportStatuses).toHaveBeenCalledTimes(2)
	})

	it("keeps waiting through a failed request", async () => {
		getReportStatuses.mockRejectedValueOnce(new Error("Network Error"))
		getReportStatuses.mockImplementation(() => answer([status(5, "completed")]))
		const store = useReportGenerationStore()
		store.track({ id: 5, name: "Weekly" })
		await tick(3_000)
		expect(store.isPending(5)).toBe(true)
		await tick(3_000)
		expect(store.pending).toEqual([])
		expect(prepend).toHaveBeenCalledTimes(1)
	})

	it("asks about at most one batch at a time, the rest on the next poll", async () => {
		getReportStatuses.mockImplementation((ids: number[]) => answer(ids.map(id => status(id, "completed"))))
		const store = useReportGenerationStore()
		for (let id = 1; id <= STATUS_BATCH + 2; id++) store.track({ id, name: `r${id}` })
		await tick(3_000)
		expect(getReportStatuses.mock.calls[0]![0]).toHaveLength(STATUS_BATCH)
		expect(store.pending.map(r => r.id)).toEqual([STATUS_BATCH + 1, STATUS_BATCH + 2])
		await tick(3_000)
		expect(getReportStatuses.mock.calls[1]![0]).toEqual([STATUS_BATCH + 1, STATUS_BATCH + 2])
		expect(store.pending).toEqual([])
	})

	it("stops on logout", async () => {
		getReportStatuses.mockImplementation(() => answer([status(5, "processing")]))
		const store = useReportGenerationStore()
		store.track({ id: 5, name: "Weekly" })
		store.reset()
		await tick(60_000)
		expect(getReportStatuses).not.toHaveBeenCalled()
	})

	it("picks up again after a reload, from the persisted list", async () => {
		getReportStatuses.mockImplementation(() => answer([status(7, "completed")]))
		const store = useReportGenerationStore()
		store.$patch({ pending: [{ id: 7, name: "Kept", startedAt: Date.now() - 120_000 }] })
		store.resume()
		await tick(10_000) // running for two minutes already: the 10 s pace
		expect(getReportStatuses).toHaveBeenCalledWith([7])
	})
})
