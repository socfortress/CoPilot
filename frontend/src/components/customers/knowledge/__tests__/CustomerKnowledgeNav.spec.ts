/**
 * The Knowledge pane's bar of jumps: one per group of facts and one for "What Talon sees", shown
 * only over a list of facts, jumping to the part asked for and marking it as the current one.
 */
import type { KnowledgeItem } from "@/types/customer-knowledge"
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import CustomerKnowledge from "../CustomerKnowledge.vue"
import CustomerKnowledgeNav from "../CustomerKnowledgeNav.vue"
import { KINDS } from "../knowledge"

const list = vi.fn()

vi.mock("@/api", () => ({
	default: {
		customerKnowledge: {
			list: (...a: unknown[]) => list(...a),
			whatTalonSees: vi.fn()
		}
	}
}))

// The fact component is stubbed: only the kind matters here, never the value.
function fact(id: number, kind: KnowledgeItem["kind"]): KnowledgeItem {
	return {
		id,
		customer_code: "ACME",
		branch: "network",
		kind,
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
	} as KnowledgeItem
}

async function render() {
	const wrapper = mount(CustomerKnowledge, {
		props: { customerCode: "ACME" },
		attachTo: document.body,
		global: {
			stubs: { CustomerKnowledgeForm: true, CustomerKnowledgeFact: true, CustomerKnowledgeSees: true, Icon: true }
		}
	})
	await flushPromises()
	return wrapper
}

const scrollIntoView = vi.fn()

enableAutoUnmount(afterEach)

beforeEach(() => {
	setActivePinia(createPinia())
	scrollIntoView.mockReset()
	Element.prototype.scrollIntoView = scrollIntoView
	list.mockReset().mockResolvedValue({
		data: { success: true, items: [fact(1, "network_zone"), fact(2, "network_zone"), fact(3, "account_role")] }
	})
})

describe("the bar of jumps", () => {
	it("lists every group with its count, then What Talon sees", async () => {
		const wrapper = await render()
		const links = wrapper.findAll(".knowledge-nav-link")
		expect(links.map(link => link.attributes("data-testid"))).toEqual([
			...KINDS.map(kind => `knowledge-nav-${kind}`),
			"knowledge-nav-talon"
		])
		expect(wrapper.get('[data-testid="knowledge-nav-network_zone"]').text()).toBe("Network zones 2")
		expect(wrapper.get('[data-testid="knowledge-nav-account_role"]').text()).toBe("Accounts 1")
		expect(wrapper.get('[data-testid="knowledge-nav-talon"]').text()).toBe("What Talon sees")
	})

	it("marks the first part current before anything scrolls", async () => {
		const wrapper = await render()
		const current = wrapper.findAll('[aria-current="true"]')
		expect(current).toHaveLength(1)
		expect(current[0].attributes("data-testid")).toBe(`knowledge-nav-${KINDS[0]}`)
	})

	it("jumps to the group asked for and marks it current", async () => {
		const wrapper = await render()
		await wrapper.get('[data-testid="knowledge-nav-account_role"]').trigger("click")
		expect(scrollIntoView).toHaveBeenCalledTimes(1)
		const target = scrollIntoView.mock.contexts[0] as HTMLElement
		expect(target.getAttribute("data-knowledge-anchor")).toBe("account_role")
		expect(target.getAttribute("data-testid")).toBe("knowledge-group-account_role")
		expect(wrapper.get('[data-testid="knowledge-nav-account_role"]').attributes("aria-current")).toBe("true")
	})

	it("jumps to What Talon sees", async () => {
		const wrapper = await render()
		await wrapper.get('[data-testid="knowledge-nav-talon"]').trigger("click")
		const target = scrollIntoView.mock.contexts[0] as HTMLElement
		expect(target.getAttribute("data-knowledge-anchor")).toBe("talon")
	})

	it("isn't shown over the empty state", async () => {
		list.mockResolvedValue({ data: { success: true, items: [] } })
		const wrapper = await render()
		expect(wrapper.findComponent(CustomerKnowledgeNav).exists()).toBe(false)
	})

	it("isn't shown when the facts fail", async () => {
		list.mockRejectedValue(new Error("down"))
		const wrapper = await render()
		expect(wrapper.findComponent(CustomerKnowledgeNav).exists()).toBe(false)
	})

	it("isn't shown over the form", async () => {
		const wrapper = await render()
		await wrapper.get('[data-testid="knowledge-add-network_zone"]').trigger("click")
		await flushPromises()
		expect(wrapper.findComponent(CustomerKnowledgeNav).exists()).toBe(false)
	})
})
