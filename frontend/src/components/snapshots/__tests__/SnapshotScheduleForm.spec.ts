import type { IndexPatternPreview, SnapshotScheduleResponse } from "@/types/snapshots"
import { flushPromises, mount } from "@vue/test-utils"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import SnapshotScheduleForm from "../SnapshotScheduleForm.vue"
import { PREVIEW_DEBOUNCE_MS } from "../useIndexPatternPreview"

const getRepositories = vi.fn()
const previewSchedulePattern = vi.fn()
const createSchedule = vi.fn()
const updateSchedule = vi.fn()

vi.mock("@/api", () => ({
	default: {
		snapshots: {
			getRepositories: (...a: unknown[]) => getRepositories(...a),
			previewSchedulePattern: (...a: unknown[]) => previewSchedulePattern(...a),
			createSchedule: (...a: unknown[]) => createSchedule(...a),
			updateSchedule: (...a: unknown[]) => updateSchedule(...a)
		}
	}
}))
vi.mock("naive-ui", async original => ({
	...(await original<typeof import("naive-ui")>()),
	useMessage: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() })
}))

const FULL_PATTERN = "fortinet-*,palo_alto-*,wazuh-*,-wazuh-monitoring-*,-*-poc_*"

function answer(preview: Partial<IndexPatternPreview>) {
	return {
		data: {
			success: true,
			message: "",
			index_pattern: FULL_PATTERN,
			problem: null,
			matching_index_count: null,
			matching_indices: [],
			truncated: false,
			...preview
		}
	}
}

function deferred<T>() {
	let resolve!: (value: T) => void
	const promise = new Promise<T>(r => (resolve = r))
	return { promise, resolve }
}

function patternInput(wrapper: ReturnType<typeof mount>) {
	return wrapper.find('input[placeholder="e.g., fortinet-*,wazuh-*,-wazuh-monitoring-*"]')
}

function previewText(wrapper: ReturnType<typeof mount>) {
	return wrapper.find('[data-testid="pattern-preview"]').text()
}

async function settle() {
	await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS)
	await flushPromises()
}

async function showMatches(wrapper: ReturnType<typeof mount>) {
	const show = wrapper.findAll("button").find(button => button.text() === "Show")
	if (!show) throw new Error("the preview has no Show button")
	await show.trigger("click")
}

describe("snapshot schedule form: the index pattern", () => {
	beforeEach(() => {
		vi.useFakeTimers()
		getRepositories.mockResolvedValue({ data: { success: true, repositories: [] } })
		previewSchedulePattern.mockReset()
		createSchedule.mockReset()
		updateSchedule.mockReset()
	})
	afterEach(() => vi.useRealTimers())

	it("explains the syntax under the field", () => {
		const wrapper = mount(SnapshotScheduleForm)
		expect(wrapper.text()).toContain("Separate patterns with commas.")
		expect(wrapper.text()).toContain("excludes the indices it matches, wherever it is in the list")
	})

	it("says how many indices a pattern matches as it is typed, and lists them on request", async () => {
		previewSchedulePattern.mockResolvedValue(
			answer({
				matching_index_count: 3,
				matching_indices: ["fortinet-acme_12", "palo_alto-globex_4", "wazuh-acme_30"]
			})
		)
		const wrapper = mount(SnapshotScheduleForm)

		await patternInput(wrapper).setValue(FULL_PATTERN)
		expect(previewText(wrapper)).toContain("Checking which indices match")
		await settle()

		expect(previewSchedulePattern).toHaveBeenCalledTimes(1)
		expect(previewSchedulePattern.mock.calls[0][0]).toBe(FULL_PATTERN)
		expect(previewText(wrapper)).toContain("Matches 3 indices right now")
		expect(wrapper.find('[data-testid="pattern-preview-indices"]').exists()).toBe(false)

		await showMatches(wrapper)
		expect(wrapper.find('[data-testid="pattern-preview-indices"]').text()).toContain("palo_alto-globex_4")
	})

	it("says how many more match than it lists", async () => {
		previewSchedulePattern.mockResolvedValue(
			answer({ matching_index_count: 250, matching_indices: ["fortinet-acme_0"], truncated: true })
		)
		const wrapper = mount(SnapshotScheduleForm)

		await patternInput(wrapper).setValue("fortinet-*")
		await settle()
		await showMatches(wrapper)

		expect(previewText(wrapper)).toContain("Matches 250 indices right now")
		expect(wrapper.find('[data-testid="pattern-preview-indices"]').text()).toContain("and 249 more")
	})

	it("warns when a pattern matches nothing", async () => {
		previewSchedulePattern.mockResolvedValue(answer({ matching_index_count: 0 }))
		const wrapper = mount(SnapshotScheduleForm)

		await patternInput(wrapper).setValue("pfsense-*")
		await settle()

		expect(previewText(wrapper)).toContain("Matches no index right now")
	})

	it("shows the backend's reason when a schedule can't be saved with the pattern", async () => {
		const problem = "The pattern only excludes indices: add at least one part to include, for example wazuh-*"
		previewSchedulePattern.mockResolvedValue(answer({ problem }))
		const wrapper = mount(SnapshotScheduleForm)

		await patternInput(wrapper).setValue("-wazuh-monitoring-*")
		await settle()

		expect(previewText(wrapper)).toContain(problem)
	})

	it("says so when the indexer can't be asked", async () => {
		previewSchedulePattern.mockRejectedValue(new Error("Request failed with status code 502"))
		const wrapper = mount(SnapshotScheduleForm)

		await patternInput(wrapper).setValue("fortinet-*")
		await settle()

		expect(previewText(wrapper)).toContain("Couldn't check which indices match")
	})

	it("asks once for what was typed last, and drops the answer to a pattern typed over", async () => {
		const first = deferred<ReturnType<typeof answer>>()
		previewSchedulePattern.mockImplementationOnce(() => first.promise)
		previewSchedulePattern.mockResolvedValueOnce(answer({ matching_index_count: 2, matching_indices: ["a", "b"] }))
		const wrapper = mount(SnapshotScheduleForm)

		// Keystrokes inside the debounce: one request.
		await patternInput(wrapper).setValue("f")
		await patternInput(wrapper).setValue("fo")
		await patternInput(wrapper).setValue("fortinet-*")
		await settle()
		expect(previewSchedulePattern).toHaveBeenCalledTimes(1)
		expect(previewSchedulePattern.mock.calls[0][0]).toBe("fortinet-*")

		// A new pattern while that check runs: it is aborted, and its late answer changes nothing.
		await patternInput(wrapper).setValue("fortinet-*,wazuh-*")
		const firstSignal = previewSchedulePattern.mock.calls[0][1] as AbortSignal
		expect(firstSignal.aborted).toBe(true)
		await settle()
		first.resolve(answer({ matching_index_count: 99 }))
		await flushPromises()

		expect(previewText(wrapper)).toContain("Matches 2 indices right now")
	})

	it("checks an existing schedule's pattern when it opens", async () => {
		previewSchedulePattern.mockResolvedValue(answer({ matching_index_count: 1, matching_indices: ["wazuh-acme_30"] }))
		const schedule = {
			id: 7,
			name: "Daily cold storage",
			index_pattern: "wazuh-*,-wazuh-monitoring-*",
			repository: "cold",
			enabled: true,
			snapshot_prefix: "scheduled",
			include_global_state: false,
			skip_write_indices: true,
			retention_days: 365,
			interval_days: 1,
			timezone: "UTC",
			created_at: "2026-11-01T00:00:00",
			updated_at: "2026-11-01T00:00:00"
		} as SnapshotScheduleResponse
		const wrapper = mount(SnapshotScheduleForm, { props: { schedule } })

		await settle()

		expect(previewSchedulePattern.mock.calls[0][0]).toBe("wazuh-*,-wazuh-monitoring-*")
		expect(previewText(wrapper)).toContain("Matches 1 index right now")
	})
})
