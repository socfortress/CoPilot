/**
 * Who may change what on a customer's event sources. A source's index pattern decides which
 * customer's events it reads (Event Search, the dashboards, the Customer Portal), so the API lets
 * only an admin add a source, change a pattern or delete a source; an analyst edits the rest of
 * their own customers' sources. The page offers each person only what the API will accept.
 */
import type { EventSource } from "@/types/event-sources"
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { NDialogProvider, NMessageProvider } from "naive-ui"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import CustomerEventSources from "../CustomerEventSources.vue"

const getEventSources = vi.fn()
const updateEventSource = vi.fn()
const auth = { isAdmin: true }

vi.mock("@/api", () => ({
	default: {
		siem: {
			getEventSources: (...args: unknown[]) => getEventSources(...args),
			updateEventSource: (...args: unknown[]) => updateEventSource(...args),
			createEventSource: vi.fn(),
			deleteEventSource: vi.fn()
		}
	}
}))
vi.mock("@/stores/auth", () => ({ useAuthStore: () => auth }))

const EDR: EventSource = {
	id: 1,
	customer_code: "ACME",
	name: "EDR",
	index_pattern: "wazuh-acme_*",
	event_type: "EDR",
	time_field: "timestamp",
	enabled: true,
	displayed_columns: null,
	created_at: "2026-11-01T00:00:00",
	updated_at: "2026-11-01T00:00:00"
}

function listed(sources: EventSource[]) {
	return { data: { success: true, message: "", event_sources: sources } }
}

async function render(sources: EventSource[] = [EDR]) {
	getEventSources.mockResolvedValue(listed(sources))
	const Host = defineComponent({
		render: () =>
			h(NMessageProvider, () => h(NDialogProvider, () => h(CustomerEventSources, { customerCode: "ACME" })))
	})
	const wrapper = mount(Host, { global: { stubs: { Icon: true } } })
	await flushPromises()
	return wrapper
}

type Page = Awaited<ReturnType<typeof render>>

async function openEdit(wrapper: Page) {
	await wrapper.get('[data-testid="event-source-edit"]').trigger("click")
	await flushPromises()
}

function button(wrapper: Page, label: string) {
	const found = wrapper.findAll("button").find(b => b.text().trim() === label)
	if (!found) throw new Error(`no "${label}" button`)
	return found
}

enableAutoUnmount(afterEach)

beforeEach(() => {
	getEventSources.mockReset()
	updateEventSource.mockReset()
	auth.isAdmin = true
})

describe("customer event sources by role", () => {
	it("lets an admin add, edit and delete sources, pattern included", async () => {
		const wrapper = await render()
		expect(wrapper.find('[data-testid="event-sources-add-header"]').exists()).toBe(true)
		expect(wrapper.find('[data-testid="event-source-delete"]').exists()).toBe(true)

		await openEdit(wrapper)
		expect(wrapper.get('[data-testid="event-source-pattern"]').classes()).not.toContain("n-input--disabled")
		expect(wrapper.find('[data-testid="event-source-pattern-admin-only"]').exists()).toBe(false)
	})

	it("lets an analyst edit a source but not its pattern, and add or delete none", async () => {
		auth.isAdmin = false
		updateEventSource.mockResolvedValue({ data: { success: true, message: "Event source updated successfully" } })
		const wrapper = await render()
		expect(wrapper.find('[data-testid="event-sources-add-header"]').exists()).toBe(false)
		expect(wrapper.find('[data-testid="event-source-delete"]').exists()).toBe(false)

		await openEdit(wrapper)
		expect(wrapper.get('[data-testid="event-source-pattern"]').classes()).toContain("n-input--disabled")
		expect(wrapper.get('[data-testid="event-source-pattern-admin-only"]').text()).toContain("Only an admin")

		await button(wrapper, "Update").trigger("click")
		await flushPromises()
		// The unchanged pattern still goes with the save, which the API accepts from an analyst.
		expect(updateEventSource).toHaveBeenCalledWith(1, expect.objectContaining({ index_pattern: "wazuh-acme_*" }))
	})

	it("tells an analyst on an empty tab that only an admin can add a source", async () => {
		auth.isAdmin = false
		const wrapper = await render([])
		expect(wrapper.find('[data-testid="event-sources-add"]').exists()).toBe(false)
		expect(wrapper.text()).toContain("Only an admin can add one.")
	})

	it("offers an admin the empty tab's add button", async () => {
		const wrapper = await render([])
		expect(wrapper.find('[data-testid="event-sources-add"]').exists()).toBe(true)
		expect(wrapper.text()).not.toContain("Only an admin can add one.")
	})
})
