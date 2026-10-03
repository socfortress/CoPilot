import { flushPromises, mount } from "@vue/test-utils"
import { NDialogProvider, NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"
import ComplianceDetail from "../ComplianceDetail.vue"
import ComplianceIndex from "../ComplianceIndex.vue"
import CoverageGapsIndex from "../CoverageGapsIndex.vue"
import StoriesIndex from "../StoriesIndex.vue"
import StoryDetail from "../StoryDetail.vue"
import WazuhRulesIndex from "../WazuhRulesIndex.vue"

// Every API call stays pending: these specs are about the modal header, not the data.
vi.mock("@/api", () => {
	const pending = () => new Promise(() => {})
	const namespace = new Proxy({}, { get: () => pending })
	return { default: new Proxy({}, { get: () => namespace }) }
})

/** The catalog's detail routes, by the names the useNavigation helpers resolve. */
function router() {
	const blank = { render: () => null }
	return createRouter({
		history: createMemoryHistory(),
		routes: [
			{ path: "/", component: blank },
			{ path: "/detection-catalog", name: "DetectionCatalog", component: blank },
			{ path: "/detection-catalog/stories/:name", name: "DetectionCatalogStory", component: blank },
			{ path: "/detection-catalog/detections/:id", name: "DetectionCatalogDetection", component: blank },
			{ path: "/detection-catalog/wazuh-rules/:id", name: "DetectionCatalogWazuhRule", component: blank },
			{ path: "/detection-catalog/coverage-gaps/:techniqueId", name: "DetectionCatalogCoverageGap", component: blank },
			{
				path: "/detection-catalog/compliance/:framework/:control",
				name: "DetectionCatalogComplianceGroup",
				component: blank
			}
		]
	})
}

// The detail bodies load their own data; a stub is enough to fill the modal.
const stubs = {
	WazuhRuleDetail: true,
	RuleCardContent: true,
	StoryDetail: true,
	CoverageGapDetails: true,
	ComplianceDetail: true,
	WazuhLogTest: true
}

async function render(component: unknown, props: Record<string, unknown> = {}, stubbed = stubs) {
	const appRouter = router()
	await appRouter.push("/detection-catalog")
	await appRouter.isReady()
	const Host = defineComponent({
		setup: () => () =>
			h(NMessageProvider, null, {
				default: () => h(NDialogProvider, null, { default: () => h(component as never, props) })
			})
	})
	const wrapper = mount(Host, { attachTo: document.body, global: { plugins: [appRouter], stubs: stubbed } })
	await flushPromises()
	// The component's own setup state, to open a modal the way its row click would.
	const inner = wrapper.findComponent(component as never) as unknown as { vm: Record<string, unknown> }
	return { wrapper, appRouter, state: inner.vm }
}

/** The page button of the open modal (n-modal teleports to the body). */
function pageButton() {
	return document.querySelector<HTMLAnchorElement>("[data-testid=modal-page-button]")
}

async function openAndFollow(
	state: Record<string, unknown>,
	open: () => void,
	appRouter: ReturnType<typeof router>,
	href: string
) {
	open()
	await nextTick()
	await flushPromises()
	const button = pageButton()
	expect(button?.getAttribute("href")).toBe(href)
	button?.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, button: 0 }))
	await flushPromises()
	expect(appRouter.currentRoute.value.fullPath).toBe(href)
	return state
}

beforeEach(() => setActivePinia(createPinia()))
afterEach(() => {
	document.body.innerHTML = ""
})

describe("detection catalog modals open their entity's page from the header", () => {
	it("a Wazuh rule, from the rules grid", async () => {
		const { appRouter, state } = await render(WazuhRulesIndex)
		await openAndFollow(state, () => (state.modalRuleId = 5710), appRouter, "/detection-catalog/wazuh-rules/5710")
		expect(state.modalRuleId).toBeNull() // the modal closed
	})

	it("a Wazuh rule, from a compliance control", async () => {
		const { appRouter, state } = await render(
			ComplianceDetail,
			{ group: { control: "10.2.4", rule_count: 1, rule_ids: [5503], total_hits_30d: 4, total_hits_7d: 1 } },
			{ ...stubs, ComplianceDetail: false }
		)
		await openAndFollow(
			state,
			() => {
				state.modalRuleId = 5503
				state.showDetailModal = true
			},
			appRouter,
			"/detection-catalog/wazuh-rules/5503"
		)
		expect(state.showDetailModal).toBe(false)
	})

	it("a compliance control, in its framework", async () => {
		const { appRouter, state } = await render(ComplianceIndex)
		await openAndFollow(
			state,
			() => (state.modalGroup = { control: "10.2.4", rule_count: 3, rule_ids: [], total_hits_30d: 9, total_hits_7d: 2 }),
			appRouter,
			"/detection-catalog/compliance/pci_dss/10.2.4"
		)
		expect(state.modalGroup).toBeNull()
	})

	it("a coverage gap", async () => {
		const { appRouter, state } = await render(CoverageGapsIndex)
		await openAndFollow(
			state,
			() => (state.selectedGap = { technique_id: "T1059", technique_name: "Command and Scripting Interpreter" }),
			appRouter,
			"/detection-catalog/coverage-gaps/T1059"
		)
		expect(state.selectedGap).toBeNull()
	})

	it("an analytic story, whose name carries spaces and punctuation", async () => {
		const { appRouter, state } = await render(StoriesIndex)
		const name = "Suspicious Command-Line Executions: Windows"
		await openAndFollow(
			state,
			() => {
				state.selectedStoryName = name
				state.showStoryModal = true
			},
			appRouter,
			appRouter.resolve({ name: "DetectionCatalogStory", params: { name } }).href
		)
		expect(state.showStoryModal).toBe(false)
	})

	it("a detection, from its story", async () => {
		const { appRouter, state } = await render(StoryDetail, {}, { ...stubs, StoryDetail: false })
		await openAndFollow(
			state,
			() => {
				state.modalRuleId = "abc-123"
				state.showRuleModal = true
			},
			appRouter,
			"/detection-catalog/detections/abc-123"
		)
		expect(state.showRuleModal).toBe(false)
	})
})
