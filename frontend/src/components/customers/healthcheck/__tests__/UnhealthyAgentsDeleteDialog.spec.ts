import type { VueWrapper } from "@vue/test-utils"
import type { CustomerAgentHealth, UnhealthyAgentVerdict, UnhealthyDeleteThreshold } from "@/types/customers"
import { flushPromises, mount } from "@vue/test-utils"
import { NInput, NInputNumber, NModal, NRadioGroup, NSelect, NSwitch } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import UnhealthyAgentsDeleteDialog from "../UnhealthyAgentsDeleteDialog.vue"

/**
 * The dialog that deletes the healthcheck list's selected agents (#1291): it reads the backend's
 * judgement at the chosen threshold, deletes exactly what it showed, in chunks, and says what happened.
 */

const customers = vi.hoisted(() => ({
	previewUnhealthyAgentsDeletion: vi.fn(),
	deleteUnhealthyAgents: vi.fn()
}))
vi.mock("@/api", () => ({ default: { customers } }))

/** What the mocked backend judges each agent to be; anything else is deletable. */
let verdicts: Record<string, UnhealthyAgentVerdict> = {}

function health(agentId: string): CustomerAgentHealth {
	return { agent_id: agentId, hostname: `host-${agentId}`, id: Number(agentId) } as CustomerAgentHealth
}

function previewAnswer(ids: string[], notSeenFor: UnhealthyDeleteThreshold) {
	const agents = ids.map(id => ({
		agent_id: id,
		verdict: verdicts[id] ?? "deletable",
		hostname: `host-${id}`,
		label: null,
		os: "Windows",
		last_seen: "2026-09-01T10:00:00",
		other_last_seen: "2026-09-01T10:00:00"
	}))
	const counts = { deletable: 0, active_elsewhere: 0, seen_recently: 0, wazuh_manager: 0, not_found: 0 }
	for (const agent of agents) counts[agent.verdict] += 1
	return {
		data: {
			success: true,
			source: "wazuh",
			not_seen_for: notSeenFor,
			cutoff: "2026-09-22T10:00:00",
			counts,
			agents
		}
	}
}

function deleteAnswer(ids: string[]) {
	return {
		data: {
			success: true,
			source: "wazuh",
			not_seen_for: { value: 30, unit: "days" },
			requested: ids.length,
			deleted: ids.length,
			skipped: 0,
			failed: 0,
			unconfirmed: 0,
			results: ids.map(id => ({
				agent_id: id,
				hostname: `host-${id}`,
				outcome: "deleted",
				reason: null,
				unconfirmed: []
			}))
		}
	}
}

let wrapper: VueWrapper | null = null

/** The mounted wrapper; a test that forgot to render fails here, by name. */
function current(): VueWrapper {
	if (!wrapper) throw new Error("render() first")
	return wrapper
}

/** ``value``, or a failure naming what was missing. */
function must<T>(value: T | null | undefined, what: string): T {
	if (value === null || value === undefined) throw new Error(`${what} not found`)
	return value
}

async function render(agentIds: string[], listFilter: Record<string, unknown> = { time: 30, unit: "days" }) {
	wrapper = mount(UnhealthyAgentsDeleteDialog, {
		props: { show: true, source: "wazuh", customerCode: "ACME", agents: agentIds.map(health), listFilter },
		attachTo: document.body
	})
	await flushPromises()
	return wrapper
}

const $ = (testId: string) => document.querySelector<HTMLElement>(`[data-testid="${testId}"]`)
const text = (testId: string) => $(testId)?.textContent?.replace(/\s+/g, " ").trim() ?? ""
const confirmButton = () => $("unhealthy-delete-confirm") as HTMLButtonElement

async function settle(ms = 0) {
	if (ms) await new Promise(resolve => setTimeout(resolve, ms))
	await flushPromises()
}

/** Past the dialog's 300 ms debounce on threshold changes. */
const DEBOUNCE = 350

async function setThreshold(value: number | null, unit?: "hours" | "days") {
	if (unit) current().findComponent(NSelect).vm.$emit("update:value", unit)
	current().findComponent(NInputNumber).vm.$emit("update:value", value)
	await settle(DEBOUNCE)
}

async function type(value: string) {
	const input = must(
		current()
			.findAllComponents(NInput)
			.find(item => item.attributes("data-testid") === "unhealthy-delete-typed"),
		"the typed confirmation"
	)
	input.vm.$emit("update:value", value)
	await flushPromises()
}

beforeEach(() => {
	setActivePinia(createPinia())
	verdicts = {}
	customers.previewUnhealthyAgentsDeletion.mockReset()
	customers.deleteUnhealthyAgents.mockReset()
	customers.previewUnhealthyAgentsDeletion.mockImplementation(async (_code, _source, body) =>
		previewAnswer(body.agent_ids, body.not_seen_for)
	)
	customers.deleteUnhealthyAgents.mockImplementation(async (_code, _source, body) => deleteAnswer(body.agent_ids))
})

afterEach(() => {
	wrapper?.unmount()
	wrapper = null
	document.body.innerHTML = ""
})

describe("unhealthy agents delete dialog: the preview", () => {
	it("reads the backend's judgement at the list's threshold and shows what it would do", async () => {
		verdicts = { "002": "active_elsewhere", "003": "seen_recently", "000": "wazuh_manager" }
		await render(["001", "002", "003", "000"])

		expect(customers.previewUnhealthyAgentsDeletion).toHaveBeenCalledTimes(1)
		expect(customers.previewUnhealthyAgentsDeletion).toHaveBeenCalledWith(
			"ACME",
			"wazuh",
			{ agent_ids: ["001", "002", "003", "000"], not_seen_for: { value: 30, unit: "days" } },
			expect.any(AbortSignal)
		)
		expect(text("unhealthy-delete-scope")).toBe("Wazuh healthcheck · ACME")
		expect(text("unhealthy-delete-count")).toContain("1")
		expect(text("unhealthy-delete-active-elsewhere")).toBe("1")
		expect(text("unhealthy-delete-kept")).toBe("2")
		expect(text("unhealthy-delete-cutoff")).toContain("Last seen before")
		const rows = [...document.querySelectorAll<HTMLElement>("[data-testid=unhealthy-delete-agents] li")]
		expect(rows.map(row => [row.dataset.agent, row.dataset.verdict])).toEqual([
			["001", "deletable"],
			["002", "active_elsewhere"],
			["003", "seen_recently"],
			["000", "wazuh_manager"]
		])
		// Kept agents say why.
		expect(rows[3].textContent).toContain("Wazuh manager")
		expect(confirmButton().disabled).toBe(false)
		expect(confirmButton().textContent).toContain("Delete 1 agent")
	})

	it("starts at 30 days when the list's filter could not delete, and reads again on a change", async () => {
		await render(["001"], { time: 2, unit: "hours" })
		expect(customers.previewUnhealthyAgentsDeletion.mock.calls[0][2].not_seen_for).toEqual({
			value: 30,
			unit: "days"
		})

		await setThreshold(90)
		expect(customers.previewUnhealthyAgentsDeletion).toHaveBeenCalledTimes(2)
		expect(customers.previewUnhealthyAgentsDeletion.mock.calls[1][2].not_seen_for).toEqual({
			value: 90,
			unit: "days"
		})

		current().findComponent(NRadioGroup).vm.$emit("update:value", "7d")
		await settle(DEBOUNCE)
		expect(customers.previewUnhealthyAgentsDeletion.mock.calls[2][2].not_seen_for).toEqual({
			value: 7,
			unit: "days"
		})
	})

	it("asks once on open, and again when the threshold comes back after a request it dropped", async () => {
		await render(["001"])
		await settle(DEBOUNCE)
		expect(customers.previewUnhealthyAgentsDeletion).toHaveBeenCalledTimes(1)

		// A 60-day preview on its way, dropped by an invalid value, then 60 days again: asked again.
		customers.previewUnhealthyAgentsDeletion.mockImplementationOnce(() => new Promise(() => {}))
		await setThreshold(60)
		await setThreshold(null)
		expect(text("unhealthy-delete-problem")).toMatch(/choose/i)
		await setThreshold(60)
		expect(customers.previewUnhealthyAgentsDeletion).toHaveBeenCalledTimes(3)
		expect(confirmButton().disabled).toBe(false)
	})

	it("refuses a threshold under 24 hours before asking anything", async () => {
		await render(["001"])
		await setThreshold(23, "hours")

		expect(text("unhealthy-delete-problem")).toMatch(/at least 24 hours/i)
		expect(customers.previewUnhealthyAgentsDeletion).toHaveBeenCalledTimes(1)
		expect(confirmButton().disabled).toBe(true)
		expect(text("unhealthy-delete-count")).toContain("—")
	})

	it("never acts on a preview read at another threshold", async () => {
		await render(["001"])
		let release: (value: unknown) => void = () => {}
		customers.previewUnhealthyAgentsDeletion.mockImplementationOnce(
			(_code, _source, body) =>
				new Promise(resolve => {
					release = () => resolve(previewAnswer(body.agent_ids, body.not_seen_for))
				})
		)
		await setThreshold(60)
		// The 30-day preview is on screen, the 60-day one is still on its way: nothing to confirm.
		expect(confirmButton().disabled).toBe(true)
		release(null)
		await settle()
		expect(confirmButton().disabled).toBe(false)
	})

	it("says a preview failed and reads it again on Retry", async () => {
		customers.previewUnhealthyAgentsDeletion.mockRejectedValueOnce({
			response: { data: { success: false, message: "Customer with customer_code ACME not found" } }
		})
		await render(["001"])
		expect(document.body.textContent).toContain("Customer with customer_code ACME not found")
		expect(confirmButton().disabled).toBe(true)

		const retry = must(
			[...document.querySelectorAll("button")].find(button => button.textContent?.includes("Retry")),
			"Retry"
		)
		retry.click()
		await settle()
		expect(customers.previewUnhealthyAgentsDeletion).toHaveBeenCalledTimes(2)
		expect(confirmButton().disabled).toBe(false)
	})
})

describe("unhealthy agents delete dialog: confirming", () => {
	it("under a week, cautions and asks for the count to be typed", async () => {
		await render(["001"], { time: 1, unit: "days" })

		expect($("unhealthy-delete-caution")).not.toBeNull()
		expect(confirmButton().disabled).toBe(true)
		await type("2")
		expect(confirmButton().disabled).toBe(true)
		await type("1")
		expect(confirmButton().disabled).toBe(false)
	})

	it("asks for the typed count from ten agents, whatever the threshold", async () => {
		const ids = Array.from({ length: 10 }, (_, index) => String(index + 1).padStart(3, "0"))
		await render(ids)
		expect($("unhealthy-delete-caution")).toBeNull()
		expect(confirmButton().disabled).toBe(true)
		await type("10")
		expect(confirmButton().disabled).toBe(false)
	})

	it("needs a new count when the set changes", async () => {
		verdicts = { "002": "active_elsewhere" }
		await render(["001", "002"], { time: 1, unit: "days" })
		await type("1")
		expect(confirmButton().disabled).toBe(false)

		current().findComponent(NSwitch).vm.$emit("update:value", true)
		await flushPromises()
		expect(confirmButton().textContent).toContain("Delete 2 agents")
		expect(confirmButton().disabled).toBe(true)
		// The figures still split the selection: the included agent moved to Delete.
		expect(text("unhealthy-delete-count")).toContain("2")
		expect(text("unhealthy-delete-active-elsewhere")).toBe("0")
		expect(text("unhealthy-delete-kept")).toBe("0")
	})
})

describe("unhealthy agents delete dialog: deleting", () => {
	it("sends exactly what it showed: the agents active elsewhere only when included", async () => {
		verdicts = { "002": "active_elsewhere", "003": "seen_recently" }
		await render(["001", "002", "003"])
		current().findComponent(NSwitch).vm.$emit("update:value", true)
		await flushPromises()

		confirmButton().click()
		await settle()
		expect(customers.deleteUnhealthyAgents).toHaveBeenCalledTimes(1)
		expect(customers.deleteUnhealthyAgents).toHaveBeenCalledWith("ACME", "wazuh", {
			agent_ids: ["001", "002"],
			not_seen_for: { value: 30, unit: "days" },
			include_active_elsewhere: true
		})
	})

	it("deletes in chunks of ten, one at a time, then says what happened and asks the list to reload", async () => {
		const ids = Array.from({ length: 23 }, (_, index) => String(index + 1).padStart(3, "0"))
		await render(ids)
		await type("23")
		confirmButton().click()
		await settle()

		expect(customers.deleteUnhealthyAgents.mock.calls.map(call => call[2].agent_ids.length)).toEqual([10, 10, 3])
		expect(text("unhealthy-delete-outcome")).toBe("23 agents deleted")
		expect(text("unhealthy-delete-total-deleted")).toBe("23")
		expect($("unhealthy-delete-review")).toBeNull()
		expect(current().emitted("deleted")).toEqual([[ids]])
	})

	it("cannot be closed while it runs, and stops after the current batch when asked", async () => {
		const ids = Array.from({ length: 25 }, (_, index) => String(index + 1).padStart(3, "0"))
		await render(ids)
		await type("25")
		let release: () => void = () => {}
		customers.deleteUnhealthyAgents.mockImplementationOnce(
			(_code, _source, body) =>
				new Promise(resolve => {
					release = () => resolve(deleteAnswer(body.agent_ids))
				})
		)
		confirmButton().click()
		await settle()

		const modal = current().findComponent(NModal)
		expect(modal.props("closable")).toBe(false)
		expect(modal.props("maskClosable")).toBe(false)
		expect(modal.props("closeOnEsc")).toBe(false)
		expect(text("unhealthy-delete-progress")).toBe("0 / 25")

		;($("unhealthy-delete-stop") as HTMLButtonElement).click()
		await flushPromises()
		release()
		await settle()

		expect(customers.deleteUnhealthyAgents).toHaveBeenCalledTimes(1)
		expect(text("unhealthy-delete-outcome")).toBe("Stopped: 10 of 25 deleted")
		expect(text("unhealthy-delete-total-notSent")).toBe("15")
		expect(current().findComponent(NModal).props("closable")).toBe(true)
	})

	it("stops at a failed request and says why, keeping what was done", async () => {
		const ids = Array.from({ length: 23 }, (_, index) => String(index + 1).padStart(3, "0"))
		await render(ids)
		await type("23")
		customers.deleteUnhealthyAgents
			.mockImplementationOnce(async (_code, _source, body) => deleteAnswer(body.agent_ids))
			.mockRejectedValueOnce({ response: { data: { success: false, message: "Upstream timeout" } } })
		confirmButton().click()
		await settle()

		expect(customers.deleteUnhealthyAgents).toHaveBeenCalledTimes(2)
		expect(text("unhealthy-delete-outcome")).toBe("Stopped after 10 of 23 deleted")
		expect(document.body.textContent).toContain("Upstream timeout")
		expect(text("unhealthy-delete-total-notSent")).toBe("13")
		expect(current().emitted("deleted")?.[0][0]).toHaveLength(10)
	})

	it("lists what needs a look: failures, then agents an upstream did not confirm, then the skipped", async () => {
		await render(["001", "002", "003", "004"])
		customers.deleteUnhealthyAgents.mockResolvedValueOnce({
			data: {
				success: false,
				source: "wazuh",
				not_seen_for: { value: 30, unit: "days" },
				requested: 4,
				deleted: 2,
				skipped: 1,
				failed: 1,
				unconfirmed: 1,
				results: [
					{ agent_id: "001", hostname: "host-001", outcome: "deleted", reason: null, unconfirmed: [] },
					{
						agent_id: "002",
						hostname: "host-002",
						outcome: "skipped",
						reason: "seen_recently",
						unconfirmed: []
					},
					{
						agent_id: "003",
						hostname: "host-003",
						outcome: "deleted",
						reason: null,
						unconfirmed: ["velociraptor"]
					},
					{ agent_id: "004", hostname: "host-004", outcome: "failed", reason: null, unconfirmed: [] }
				]
			}
		})
		confirmButton().click()
		await settle()

		expect(text("unhealthy-delete-outcome")).toBe("2 of 4 deleted")
		const rows = [...document.querySelectorAll<HTMLElement>("[data-testid=unhealthy-delete-review] li")]
		expect(rows.map(row => row.dataset.agent)).toEqual(["004", "003", "002"])
		expect(rows[1].textContent).toContain("Velociraptor did not confirm")
		expect(rows[2].textContent).toContain("seen recently")
		expect(document.body.textContent).toContain("may still be enrolled there")
		expect(current().emitted("deleted")).toEqual([[["001", "003"]]])
	})

	it("starts over, at the list's threshold, every time it opens", async () => {
		await render(["001"])
		await setThreshold(90)
		await current().setProps({ show: false })
		await current().setProps({ show: true })
		await flushPromises()
		const last = must(customers.previewUnhealthyAgentsDeletion.mock.calls.at(-1), "the last preview")
		expect(last[2].not_seen_for).toEqual({ value: 30, unit: "days" })
		expect(current().findComponent(NInputNumber).props("value")).toBe(30)
	})
})
