/**
 * The Knowledge pane lists its facts as cards (large) or as rows of one list (compact), the
 * viewer's choice from the bar, remembered for this browser.
 */
import type { KnowledgeItem } from "@/types/customer-knowledge"
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import CustomerKnowledge from "../CustomerKnowledge.vue"
import CustomerKnowledgeFact from "../CustomerKnowledgeFact.vue"
import { KNOWLEDGE_DENSITY_KEY } from "../useKnowledgeDensity"

const list = vi.fn()

vi.mock("@/api", () => ({
	default: {
		customerKnowledge: {
			list: (...a: unknown[]) => list(...a),
			remove: vi.fn(),
			whatTalonSees: vi.fn()
		}
	}
}))

vi.mock("naive-ui", async original => ({
	...(await original<typeof import("naive-ui")>()),
	useMessage: () => ({ success: vi.fn(), warning: vi.fn(), error: vi.fn() })
}))

function fact(id: number, note: string | null = null): KnowledgeItem {
	return {
		id,
		customer_code: "ACME",
		branch: "network",
		kind: "network_zone",
		value: { cidr: `10.0.${id}.0/24`, zone: "server" },
		note,
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

async function renderPane() {
	const wrapper = mount(CustomerKnowledge, {
		props: { customerCode: "ACME" },
		attachTo: document.body,
		global: { stubs: { CustomerKnowledgeForm: true, CustomerKnowledgeFact: true, CustomerKnowledgeSees: true, Icon: true } }
	})
	await flushPromises()
	return wrapper
}

enableAutoUnmount(afterEach)

beforeEach(() => {
	setActivePinia(createPinia())
	localStorage.clear()
	Element.prototype.scrollIntoView = vi.fn()
	list.mockReset().mockResolvedValue({ data: { success: true, items: [fact(1), fact(2)] } })
})

describe("the pane's density", () => {
	it("starts large, with the switch on the bar", async () => {
		const wrapper = await renderPane()
		const toggle = wrapper.get('[data-testid="knowledge-nav"] [data-testid="knowledge-density"]')
		expect(toggle.get('[data-testid="knowledge-density-large"]').attributes("aria-checked")).toBe("true")
		const facts = wrapper.findAllComponents(CustomerKnowledgeFact)
		expect(facts.map(item => item.props("compact"))).toEqual([false, false])
		expect(wrapper.get('[data-testid="knowledge-group-facts"]').classes()).not.toContain("knowledge-facts-compact")
	})

	it("lists the facts as rows once compact, and remembers it", async () => {
		const wrapper = await renderPane()
		await wrapper.get('[data-testid="knowledge-density-compact"]').trigger("click")
		const facts = wrapper.findAllComponents(CustomerKnowledgeFact)
		expect(facts.map(item => item.props("compact"))).toEqual([true, true])
		expect(wrapper.get('[data-testid="knowledge-group-facts"]').classes()).toContain("knowledge-facts-compact")
		expect(localStorage.getItem(KNOWLEDGE_DENSITY_KEY)).toBe("compact")
	})

	it("opens compact when this browser chose it before", async () => {
		localStorage.setItem(KNOWLEDGE_DENSITY_KEY, "compact")
		const wrapper = await renderPane()
		expect(wrapper.get('[data-testid="knowledge-density-compact"]').attributes("aria-checked")).toBe("true")
		expect(wrapper.findAllComponents(CustomerKnowledgeFact).every(item => item.props("compact"))).toBe(true)
	})
})

describe("a fact as a row", () => {
	function renderFact(compact: boolean) {
		return mount(CustomerKnowledgeFact, {
			props: { fact: fact(7, "Main datacenter, Brescia"), customerCode: "ACME", compact },
			global: { stubs: { Icon: true } }
		})
	}

	it("puts the value, its details and the note on one row, with icon-only actions", () => {
		const wrapper = renderFact(true)
		const row = wrapper.get('[data-testid="knowledge-fact"]')
		expect(row.classes()).toContain("knowledge-fact-row")
		expect(row.attributes("title")).toBe("Last changed by ana")
		expect(wrapper.get('[data-testid="knowledge-fact-headline"]').text()).toBe("10.0.7.0/24")
		expect(wrapper.get('[data-testid="knowledge-fact-note"]').attributes("title")).toBe("Main datacenter, Brescia")
		expect(wrapper.get('[data-testid="knowledge-fact-edit"]').attributes("aria-label")).toBe("Edit fact")
		expect(wrapper.get('[data-testid="knowledge-fact-edit"]').text()).toBe("")
		expect(wrapper.get('[data-testid="knowledge-fact-delete"]').attributes("aria-label")).toBe("Delete fact")
	})

	it("keeps the card, with worded actions, when large", () => {
		const wrapper = renderFact(false)
		expect(wrapper.find(".knowledge-fact-row").exists()).toBe(false)
		expect(wrapper.get('[data-testid="knowledge-fact-changed"]').text()).toBe("Last changed by ana")
		expect(wrapper.get('[data-testid="knowledge-fact-edit"]').text()).toBe("Edit")
		expect(wrapper.get('[data-testid="knowledge-fact-edit"]').attributes("aria-label")).toBeUndefined()
	})

	it("asks to edit from the row", async () => {
		const wrapper = renderFact(true)
		await wrapper.get('[data-testid="knowledge-fact-edit"]').trigger("click")
		expect(wrapper.emitted("edit")).toHaveLength(1)
	})
})
