/**
 * The Knowledge section tells the customer page when a fact changes, so the count beside its name
 * follows while the section stays open. The form's rules are in `knowledge.spec.ts`.
 */
import type { KnowledgeItem } from "@/types/customer-knowledge"
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import CustomerKnowledge from "../CustomerKnowledge.vue"
import CustomerKnowledgeFact from "../CustomerKnowledgeFact.vue"
import CustomerKnowledgeForm from "../CustomerKnowledgeForm.vue"

const list = vi.fn()

vi.mock("@/api", () => ({ default: { customerKnowledge: { list: (...a: unknown[]) => list(...a) } } }))

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

async function render() {
	const wrapper = mount(CustomerKnowledge, {
		props: { customerCode: "ACME" },
		global: { stubs: { CustomerKnowledgeForm: true, CustomerKnowledgeFact: true, Icon: true } }
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
	list.mockReset().mockResolvedValue({ data: { success: true, items: [ZONE] } })
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
