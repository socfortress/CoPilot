import type { VueWrapper } from "@vue/test-utils"
import type { ListFilter } from "../unhealthyDelete"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, reactive } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"
import { routes } from "@/router/routes"
import CustomerHealthcheckList from "../CustomerHealthcheckList.vue"

/**
 * The healthcheck list's side of deleting unhealthy agents (#1291): what can be selected, what the
 * dialog is handed, and the list read again once agents are gone.
 */

const customers = vi.hoisted(() => ({
	getCustomerAgentsHealthcheckWazuh: vi.fn(),
	getCustomerAgentsHealthcheckVelociraptor: vi.fn()
}))
vi.mock("@/api", () => ({ default: { customers } }))
vi.mock("../CustomerHealthcheckDetails.vue", () => ({
	default: defineComponent({ name: "CustomerHealthcheckDetails", render: () => null })
}))
// The dialog has its own spec: here only what the list hands it and what it does after.
vi.mock("../UnhealthyAgentsDeleteDialog.vue", () => ({
	default: defineComponent({
		name: "UnhealthyAgentsDeleteDialog",
		props: ["show", "source", "customerCode", "agents", "listFilter"],
		emits: ["update:show", "deleted"],
		render: () => null
	})
}))

function health(agentId: string) {
	return {
		id: Number(agentId),
		agent_id: agentId,
		hostname: `host-${agentId}`,
		label: `label-${agentId}`,
		os: "Windows",
		ip_address: "10.0.0.1",
		wazuh_last_seen: "2026-09-01T10:00:00",
		velociraptor_last_seen: "2026-09-01T10:00:00",
		wazuh_agent_version: "v4.9.0",
		velociraptor_agent_version: "0.7.4",
		velociraptor_id: "C.1",
		critical_asset: false,
		customer_code: "ACME",
		unhealthy_wazuh_agent: null,
		unhealthy_velociraptor_agent: null,
		unhealthy_recent_logs_collected: null
	}
}

function listAnswer(healthy: string[], unhealthy: string[]) {
	return {
		data: {
			success: true,
			healthy_wazuh_agents: healthy.map(health),
			unhealthy_wazuh_agents: unhealthy.map(health)
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

async function render(filters: ListFilter = { time: 30, unit: "days" }) {
	const router = createRouter({ history: createMemoryHistory(), routes })
	const content = () =>
		h(CustomerHealthcheckList, { source: "wazuh", customerCode: "ACME", filters, "onUpdate:filters": () => {} })
	wrapper = mount(defineComponent({ setup: () => () => h(NMessageProvider, null, content) }), {
		global: { plugins: [router] },
		attachTo: document.body
	})
	await flushPromises()
	return wrapper
}

const dialog = () => current().findComponent({ name: "UnhealthyAgentsDeleteDialog" })
const deleteButton = () => current().find<HTMLButtonElement>("[data-testid=healthcheck-delete-selected]")
const count = () => current().find("[data-testid=healthcheck-selected-count]").text().replace(/\s+/g, " ")

/** The checkbox of the n-th unhealthy agent. */
async function toggle(index: number) {
	await current().findAll("[data-testid=healthcheck-select]")[index].trigger("click")
	await flushPromises()
}

beforeEach(() => {
	setActivePinia(createPinia())
	customers.getCustomerAgentsHealthcheckWazuh.mockReset()
	customers.getCustomerAgentsHealthcheckWazuh.mockResolvedValue(listAnswer(["001"], ["002", "003", "004"]))
})

afterEach(() => {
	wrapper?.unmount()
	wrapper = null
	document.body.innerHTML = ""
})

describe("customer healthcheck list: deleting unhealthy agents", () => {
	it("offers a checkbox on unhealthy agents only, and nothing to delete until one is picked", async () => {
		await render()

		expect(current().findAll("[data-testid=healthcheck-select]")).toHaveLength(3)
		expect(count()).toBe("0 / 3 selected")
		expect(deleteButton().element.disabled).toBe(true)

		await toggle(1)
		expect(count()).toBe("1 / 3 selected")
		expect(deleteButton().element.disabled).toBe(false)
	})

	it("selects all and clears", async () => {
		await render()
		await current().find("[data-testid=healthcheck-select-all]").trigger("click")
		await flushPromises()
		expect(count()).toBe("3 / 3 selected")

		const clear = must(
			current()
				.findAll("button")
				.find(button => button.text() === "Clear"),
			"Clear"
		)
		await clear.trigger("click")
		expect(count()).toBe("0 / 3 selected")
	})

	it("hands the dialog the selected agents, in list order, and the filter the list was read with", async () => {
		await render({ time: 2, unit: "days" })
		await toggle(2)
		await toggle(0)
		await deleteButton().trigger("click")

		expect(dialog().props("show")).toBe(true)
		expect(
			dialog()
				.props("agents")
				.map((agent: { agent_id: string }) => agent.agent_id)
		).toEqual(["002", "004"])
		expect(dialog().props("listFilter")).toEqual({ time: 2, unit: "days" })
		expect(dialog().props("source")).toBe("wazuh")
		expect(dialog().props("customerCode")).toBe("ACME")
	})

	it("reads the list again once agents are deleted, and starts the selection over", async () => {
		await render()
		await current().find("[data-testid=healthcheck-select-all]").trigger("click")
		await flushPromises()

		customers.getCustomerAgentsHealthcheckWazuh.mockResolvedValueOnce(listAnswer(["001"], ["004"]))
		dialog().vm.$emit("deleted", ["002", "003"])
		await flushPromises()

		expect(customers.getCustomerAgentsHealthcheckWazuh).toHaveBeenCalledTimes(2)
		expect(current().findAll("[data-testid=healthcheck-select]")).toHaveLength(1)
		// 004 was kept (it had a reason): it is not still picked for the next deletion.
		expect(count()).toBe("0 / 1 selected")
	})

	it("drops a selected agent the list no longer shows as unhealthy", async () => {
		const filters = reactive<ListFilter>({ time: 30, unit: "days" })
		await render(filters)
		await current().find("[data-testid=healthcheck-select-all]").trigger("click")
		await flushPromises()

		// The filter changes, the list is read again, and 003 is now healthy.
		customers.getCustomerAgentsHealthcheckWazuh.mockResolvedValueOnce(listAnswer(["001", "003"], ["002", "004"]))
		filters.time = 2
		await new Promise(resolve => setTimeout(resolve, 600))
		await flushPromises()

		expect(count()).toBe("2 / 2 selected")
		await deleteButton().trigger("click")
		expect(
			dialog()
				.props("agents")
				.map((agent: { agent_id: string }) => agent.agent_id)
		).toEqual(["002", "004"])
	})

	it("shows no selection bar when nothing is unhealthy", async () => {
		customers.getCustomerAgentsHealthcheckWazuh.mockResolvedValue(listAnswer(["001", "002"], []))
		await render()
		expect(current().find("[data-testid=healthcheck-selection-bar]").exists()).toBe(false)
	})
})
