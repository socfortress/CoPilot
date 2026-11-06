/**
 * The Knowledge section tells the customer page when a fact changes, so the count beside its name
 * follows while the section stays open. The form's rules are in `knowledge.spec.ts`, and the "What
 * Talon sees" panel's own states in `CustomerKnowledgeSees.spec.ts`: here, only where it sits, and
 * that the facts don't depend on it.
 */
import type { KnowledgeItem } from "@/types/customer-knowledge"
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import CustomerKnowledge from "../CustomerKnowledge.vue"
import CustomerKnowledgeFact from "../CustomerKnowledgeFact.vue"
import CustomerKnowledgeForm from "../CustomerKnowledgeForm.vue"
import CustomerKnowledgeSees from "../CustomerKnowledgeSees.vue"

const list = vi.fn()
const whatTalonSees = vi.fn()

vi.mock("@/api", () => ({
	default: {
		customerKnowledge: {
			list: (...a: unknown[]) => list(...a),
			whatTalonSees: (...a: unknown[]) => whatTalonSees(...a)
		}
	}
}))

const ZONE: KnowledgeItem = {
	id: 1,
	customer_code: "ACME",
	branch: "network",
	kind: "network_zone",
	value: { cidr: "10.0.0.0/24", zone: "server" },
	note: null,
	status: "approved",
	source: "soc",
	version: 1,
	expires_at: null,
	expired: false,
	created_at: null,
	updated_at: null,
	updated_by_username: "ana"
}

async function render(stubs: Record<string, boolean> = { CustomerKnowledgeSees: true }) {
	const wrapper = mount(CustomerKnowledge, {
		props: { customerCode: "ACME" },
		global: { stubs: { CustomerKnowledgeForm: true, CustomerKnowledgeFact: true, Icon: true, ...stubs } }
	})
	await flushPromises()
	return wrapper
}

type Page = Awaited<ReturnType<typeof render>>

async function openForm(wrapper: Page) {
	await wrapper.get('[data-testid="knowledge-add-network_zone"]').trigger("click")
	await flushPromises()
	return wrapper.getComponent(CustomerKnowledgeForm)
}

enableAutoUnmount(afterEach)

beforeEach(() => {
	setActivePinia(createPinia())
	list.mockReset().mockResolvedValue({ data: { success: true, items: [ZONE] } })
	whatTalonSees.mockReset().mockRejectedValue(new Error("Talon is down"))
})

describe("telling the page a fact changed", () => {
	it("says nothing about a read", async () => {
		const wrapper = await render()
		expect(list).toHaveBeenCalledTimes(1)
		expect(wrapper.emitted("changed")).toBeUndefined()
	})

	it.each(["submitted", "stale"])("says so when the form reports %s, and reads the facts again", async event => {
		const wrapper = await render()
		const form = await openForm(wrapper)
		form.vm.$emit(event)
		await flushPromises()
		expect(wrapper.emitted("changed")).toHaveLength(1)
		expect(list).toHaveBeenCalledTimes(2)
		expect(wrapper.findComponent(CustomerKnowledgeForm).exists()).toBe(false)
	})

	it("says so when a fact is deleted, and reads the facts again", async () => {
		const wrapper = await render()
		wrapper.getComponent(CustomerKnowledgeFact).vm.$emit("deleted")
		await flushPromises()
		expect(wrapper.emitted("changed")).toHaveLength(1)
		expect(list).toHaveBeenCalledTimes(2)
	})

	it("says nothing when the form is cancelled", async () => {
		const wrapper = await render()
		const form = await openForm(wrapper)
		form.vm.$emit("close")
		await flushPromises()
		expect(wrapper.emitted("changed")).toBeUndefined()
		expect(list).toHaveBeenCalledTimes(1)
	})
})

describe("what Talon sees", () => {
	it("sits on the normal view, after the facts", async () => {
		const wrapper = await render()
		expect(wrapper.findComponent(CustomerKnowledgeSees).exists()).toBe(true)
		const page = wrapper.html()
		expect(page.indexOf("knowledge-group-network_zone")).toBeLessThan(page.indexOf("customer-knowledge-sees"))
	})

	it("sits after the empty state too", async () => {
		list.mockResolvedValue({ data: { success: true, items: [] } })
		const wrapper = await render()
		expect(wrapper.find('[data-testid="customer-tab-empty"]').exists()).toBe(true)
		expect(wrapper.findComponent(CustomerKnowledgeSees).exists()).toBe(true)
	})

	it("is gone while the form is open, and back when it closes", async () => {
		const wrapper = await render()
		const form = await openForm(wrapper)
		expect(wrapper.findComponent(CustomerKnowledgeSees).exists()).toBe(false)
		form.vm.$emit("close")
		await flushPromises()
		expect(wrapper.findComponent(CustomerKnowledgeSees).exists()).toBe(true)
	})

	it("is told the customer", async () => {
		const wrapper = await render()
		expect(wrapper.findComponent(CustomerKnowledgeSees).props("customerCode")).toBe("ACME")
	})

	it("leaves the facts working when it fails", async () => {
		const wrapper = await render({})
		expect(wrapper.find('[data-testid="knowledge-sees-failure"]').exists()).toBe(true)
		expect(wrapper.find('[data-testid="knowledge-failure"]').exists()).toBe(false)
		expect(wrapper.findComponent(CustomerKnowledgeFact).exists()).toBe(true)
		await openForm(wrapper)
		expect(wrapper.findComponent(CustomerKnowledgeForm).exists()).toBe(true)
	})

	it("doesn't wait for a Talon that hasn't answered", async () => {
		whatTalonSees.mockReturnValue(new Promise(() => {}))
		const wrapper = await render({})
		expect(wrapper.findComponent(CustomerKnowledgeFact).exists()).toBe(true)
	})

	it("doesn't say the facts changed, and isn't read again by a fact that did", async () => {
		const wrapper = await render({})
		expect(wrapper.emitted("changed")).toBeUndefined()
		wrapper.getComponent(CustomerKnowledgeFact).vm.$emit("deleted")
		await flushPromises()
		expect(wrapper.emitted("changed")).toHaveLength(1)
		expect(whatTalonSees).toHaveBeenCalledTimes(1)
	})

	it("still shows when the facts fail", async () => {
		list.mockRejectedValue(new Error("facts are down"))
		const wrapper = await render()
		expect(wrapper.find('[data-testid="knowledge-failure"]').exists()).toBe(true)
		expect(wrapper.findComponent(CustomerKnowledgeSees).exists()).toBe(true)
	})
})
