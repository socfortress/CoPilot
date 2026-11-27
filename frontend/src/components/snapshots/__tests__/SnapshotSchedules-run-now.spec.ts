import type { ScheduleRunOutcome, SnapshotScheduleResponse } from "@/types/snapshots"
import { flushPromises, mount } from "@vue/test-utils"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import SnapshotScheduleCard from "../SnapshotScheduleCard.vue"
import SnapshotSchedules from "../SnapshotSchedules.vue"

const getSchedules = vi.fn()
const runSchedule = vi.fn()
const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() }))

vi.mock("@/api", () => ({
	default: {
		snapshots: {
			getSchedules: (...a: unknown[]) => getSchedules(...a),
			runSchedule: (...a: unknown[]) => runSchedule(...a)
		}
	}
}))
vi.mock("naive-ui", async original => ({
	...(await original<typeof import("naive-ui")>()),
	useMessage: () => toast
}))

const SNAPSHOT = "scheduled_daily_cold_storage_20261127_101500"

function schedule(overrides: Partial<SnapshotScheduleResponse> = {}): SnapshotScheduleResponse {
	return {
		id: 7,
		name: "Daily cold storage",
		index_pattern: "fortinet-*,wazuh-*,-wazuh-monitoring-*",
		repository: "cold",
		enabled: true,
		snapshot_prefix: "scheduled",
		include_global_state: false,
		skip_write_indices: true,
		retention_days: null,
		last_execution_time: null,
		last_snapshot_name: null,
		last_execution_status: null,
		scheduled_hour: 2,
		scheduled_minute: 0,
		interval_days: 1,
		day_of_week: null,
		timezone: "UTC",
		created_at: "2026-11-20T00:00:00",
		updated_at: "2026-11-20T00:00:00",
		...overrides
	}
}

function ran(outcome: ScheduleRunOutcome, status: string) {
	const started = outcome === "snapshot_started"
	return {
		data: {
			success: started || outcome === "nothing_new",
			message: `What the run did: ${outcome}`,
			outcome,
			snapshot_name: started ? SNAPSHOT : null,
			indices_snapshotted: started ? 12 : 0,
			schedule: schedule({
				last_execution_status: status,
				last_execution_time: "2026-11-27T10:15:00",
				last_snapshot_name: started ? SNAPSHOT : null
			})
		}
	}
}

function deferred<T>() {
	let resolve!: (value: T) => void
	const promise = new Promise<T>(r => (resolve = r))
	return { promise, resolve }
}

const mounted: { unmount: () => void }[] = []

async function mountSchedules(...schedules: SnapshotScheduleResponse[]) {
	getSchedules.mockResolvedValue({ data: { success: true, message: "", schedules } })
	const wrapper = mount(SnapshotSchedules)
	mounted.push(wrapper)
	await flushPromises()
	return wrapper
}

function confirmText() {
	return document.body.querySelector("[data-testid=run-now-confirm]")?.textContent ?? ""
}

async function openConfirm(wrapper: ReturnType<typeof mount>) {
	await wrapper.get("[data-testid=run-now]").trigger("click")
	await flushPromises()
}

async function answer(label: "Run now" | "Cancel") {
	const button = [...document.body.querySelectorAll<HTMLButtonElement>(".n-popconfirm__action button")].find(b =>
		b.textContent?.includes(label)
	)
	if (!button) throw new Error(`the confirmation has no ${label} button`)
	button.click()
	await flushPromises()
}

function askAgain(wrapper: ReturnType<typeof mount>) {
	wrapper.findComponent(SnapshotScheduleCard).vm.$emit("run")
	return flushPromises()
}

describe("snapshot schedules: Run now", () => {
	beforeEach(() => {
		getSchedules.mockReset()
		runSchedule.mockReset()
		for (const kind of Object.values(toast)) kind.mockReset()
	})
	afterEach(() => {
		for (const wrapper of mounted.splice(0)) wrapper.unmount()
		document.body.replaceChildren()
	})

	it("asks first, saying what the run does, and sends nothing when cancelled", async () => {
		const wrapper = await mountSchedules(schedule({ retention_days: 30, enabled: false }))

		await openConfirm(wrapper)
		expect(runSchedule).not.toHaveBeenCalled()
		expect(confirmText()).toContain("without waiting for its window")
		expect(confirmText()).toContain("It also deletes its snapshots older than 30 days.")
		expect(confirmText()).toContain("It counts as today's run: the schedule next runs on a later day.")
		expect(confirmText()).toContain("The schedule stays disabled.")

		await answer("Cancel")
		expect(runSchedule).not.toHaveBeenCalled()
	})

	it("says when a schedule with a longer interval runs next, and nothing of retention or disabling it has none of", async () => {
		const wrapper = mount(SnapshotScheduleCard, { props: { schedule: schedule({ interval_days: 7 }) } })
		mounted.push(wrapper)

		await openConfirm(wrapper)
		expect(confirmText()).toContain("It counts as a run: the schedule next runs 7 days from today at the earliest.")
		expect(confirmText()).not.toContain("deletes")
		expect(confirmText()).not.toContain("disabled")
	})

	it.each([
		["snapshot_started", "success", "SUCCESS"],
		["nothing_new", "info", "SKIPPED: No new indices to snapshot (3 write indices skipped)"],
		["no_match", "warning", "NO_MATCH: pattern matched 0 indices"],
		["failed", "error", "FAILED: indexer unreachable"]
	] as const)("runs once confirmed: %s is a %s toast, and the card shows the run", async (outcome, kind, status) => {
		runSchedule.mockResolvedValue(ran(outcome, status))
		const wrapper = await mountSchedules(schedule())

		await openConfirm(wrapper)
		await answer("Run now")

		expect(runSchedule).toHaveBeenCalledWith(7)
		expect(toast[kind]).toHaveBeenCalledWith(`What the run did: ${outcome}`, expect.objectContaining({ closable: true }))
		for (const other of Object.keys(toast).filter(name => name !== kind)) {
			expect(toast[other as keyof typeof toast]).not.toHaveBeenCalled()
		}
		// The card takes the schedule the run answered with; the list isn't read again.
		expect(getSchedules).toHaveBeenCalledTimes(1)
		expect(wrapper.text()).toContain(status.split(":")[0])
		if (outcome === "snapshot_started") expect(wrapper.text()).toContain(SNAPSHOT)
	})

	it("is busy while the run is under way, sends nothing more, and a 409 is a warning", async () => {
		const pending = deferred<ReturnType<typeof ran>>()
		runSchedule.mockReturnValueOnce(pending.promise)
		const wrapper = await mountSchedules(schedule())

		await openConfirm(wrapper)
		await answer("Run now")
		expect(wrapper.get("[data-testid=run-now]").attributes("disabled")).toBeDefined()
		await askAgain(wrapper)
		expect(runSchedule).toHaveBeenCalledTimes(1)

		pending.resolve(ran("nothing_new", "SKIPPED: No new indices to snapshot (3 write indices skipped)"))
		await flushPromises()
		expect(wrapper.get("[data-testid=run-now]").attributes("disabled")).toBeUndefined()

		// A scheduled run (or someone else's Run now) of it is under way. CoPilot's error handler
		// answers {success, message}.
		runSchedule.mockRejectedValueOnce({
			response: { status: 409, data: { success: false, message: "A run of this schedule is already under way" } }
		})
		await askAgain(wrapper)
		expect(toast.warning).toHaveBeenCalledWith("A run of this schedule is already under way.")
		expect(toast.error).not.toHaveBeenCalled()

		runSchedule.mockRejectedValueOnce({ response: { status: 500, data: { success: false, message: "Internal Server Error" } } })
		await askAgain(wrapper)
		expect(toast.error).toHaveBeenCalledWith("Internal Server Error.")
	})
})
