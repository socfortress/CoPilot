import type { UbaRollbackPlan, UbaRollbackReport } from "@/types/uba"
import { flushPromises, mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import UbaRollbackDialog from "../UbaRollbackDialog.vue"

const getRollbackPlan = vi.fn()
const rollBack = vi.fn()
const getRollback = vi.fn()

vi.mock("@/api", () => ({
	default: {
		uba: {
			getRollbackPlan: (...a: unknown[]) => getRollbackPlan(...a),
			rollBack: (...a: unknown[]) => rollBack(...a),
			getRollback: (...a: unknown[]) => getRollback(...a)
		}
	}
}))
vi.mock("@/stores/settings", () => ({ useSettingsStore: () => ({ dateFormat: { datetime: "yyyy-MM-dd HH:mm" } }) }))
vi.mock("naive-ui", async original => ({
	...(await original<typeof import("naive-ui")>()),
	useMessage: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() })
}))

const ModalStub = { template: '<div><slot /><slot name="footer" /></div>' }

function item(kind: string, title: string, detail = "", recorded = true) {
	return {
		kind,
		id: `${kind}-1`,
		title,
		source: null,
		recorded,
		detail
	}
}

const PLAN: UbaRollbackPlan = {
	remove: [
		item("routing_pipeline", "UBA ROUTING - WAZUH - acme"),
		item("output", "UBA GELF - acme", "-> 127.0.0.1:12203"),
		item("feed_stream", "UBA FEED - WAZUH - acme", "", false),
		item("uba_tenant", "UBA tenant acme", "deactivated; its data is kept", false)
	],
	keep: [item("alerts_input", "UBA ALERTS", "shared: still used by UBA ALERTS - globex")],
	conflicts: [item("alerts_stream", "UBA ALERTS - acme", "still used by event definition UBA HIGH RISK")],
	source_streams: [
		{ id: "s1", title: "ACME - Wazuh", exists: true, pipelines: ["WAZUH PROCESSING", "UBA ROUTING - WAZUH - acme"] }
	],
	uba: null,
	uba_problem: null
}

const REPORT: UbaRollbackReport = {
	id: 4,
	customer_code: "acme",
	status: "completed",
	started_at: "2026-10-13T10:00:00",
	finished_at: "2026-10-13T10:00:05",
	actor_username: "admin",
	message: "UBA rolled back for acme: 5 object(s) removed",
	steps: [{ step: "pipeline UBA ROUTING - WAZUH - acme", status: "disconnected", detail: "from 1 stream(s)" }],
	verification: [
		{ check: "pipelines of ACME - Wazuh", ok: true, detail: "1 kept: WAZUH PROCESSING" },
		{ check: "event definitions", ok: null, detail: "could not be read" }
	],
	snapshot: null
}

async function open(props: Record<string, unknown> = {}) {
	const w = mount(UbaRollbackDialog, {
		props: { customerCode: "acme", show: false, ...props },
		global: { stubs: { NModal: ModalStub, Modal: ModalStub } }
	})
	await w.setProps({ show: true })
	await flushPromises()
	return w
}

const button = (w: Awaited<ReturnType<typeof open>>, text: string) => w.findAll("button").find(b => b.text() === text)

describe("ubaRollbackDialog", () => {
	beforeEach(() => {
		getRollbackPlan.mockReset().mockResolvedValue({ data: PLAN })
		rollBack.mockReset().mockResolvedValue({ data: { report: REPORT } })
		getRollback.mockReset().mockResolvedValue({ data: { report: REPORT } })
	})

	it("previews what goes, what stays and what is left alone, without changing anything", async () => {
		const w = await open()
		expect(getRollbackPlan).toHaveBeenCalledWith("acme")
		const removed = w
			.find("[data-testid=uba-rollback-remove]")
			.findAll("li")
			.map(li => li.text())
		expect(removed[0]).toContain("UBA ROUTING - WAZUH - acme")
		expect(removed[2]).toContain("found by name")
		expect(removed[3]).not.toContain("found by name")
		expect(w.text()).toContain("shared: still used by UBA ALERTS - globex")
		expect(w.find("[data-testid=uba-rollback-conflicts]").text()).toContain("UBA HIGH RISK")
		// The customer's stream keeps its own pipeline; the UBA routing one is not listed as kept.
		expect(w.text()).toContain("pipelines: WAZUH PROCESSING")
		expect(rollBack).not.toHaveBeenCalled()
	})

	it("runs only once the customer code is typed, then shows the checks", async () => {
		const w = await open()
		const run = button(w, "Roll back UBA")
		expect(run?.attributes("disabled")).toBeDefined()
		await w.find("[data-testid=uba-rollback-confirm] input").setValue("acme")
		expect(button(w, "Roll back UBA")?.attributes("disabled")).toBeUndefined()
		await button(w, "Roll back UBA")?.trigger("click")
		await flushPromises()
		expect(rollBack).toHaveBeenCalledWith("acme")
		expect(w.emitted("done")).toHaveLength(1)
		const checks = w.findAll("[data-testid=uba-rollback-check]").map(c => c.text())
		expect(checks[0]).toContain("1 kept: WAZUH PROCESSING")
		expect(w.text()).toContain("5 object(s) removed")
	})

	it("says when there is nothing to roll back and offers no run", async () => {
		getRollbackPlan.mockResolvedValue({ data: { ...PLAN, remove: [], keep: [], conflicts: [] } })
		const w = await open()
		expect(w.text()).toContain("nothing to roll back")
		expect(button(w, "Roll back UBA")).toBeUndefined()
	})

	it("opens a past rollback's report, and offers to run a partial one again", async () => {
		getRollback.mockResolvedValue({ data: { report: { ...REPORT, status: "partial" } } })
		const w = await open({ reportId: 4 })
		expect(getRollback).toHaveBeenCalledWith("acme", 4)
		expect(getRollbackPlan).not.toHaveBeenCalled()
		await button(w, "Review and run again")?.trigger("click")
		await flushPromises()
		expect(getRollbackPlan).toHaveBeenCalledWith("acme")
	})
})
