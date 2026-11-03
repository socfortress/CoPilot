import type { Alert } from "@/types/incidentManagement/alerts"
import { flushPromises, mount } from "@vue/test-utils"
import { NDialogProvider, NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import AlertItem from "../AlertItem.vue"
import AlertOverview from "../AlertOverview.vue"

/**
 * An escalated alert says so on its card and in its details (#1331): the Escalated filter
 * selects on a flag the UI used to hide. Both show only when the flag is set.
 */

vi.mock("@/api", async () => {
	const { pendingApi } = await import("@/components/common/__tests__/modal-page-stubs")
	return { default: pendingApi() }
})
vi.mock("@/composables/useNavigation", () => ({
	useNavigation: () => ({
		routeCustomer: () => ({ navigate: vi.fn() }),
		routeIncidentManagementAlerts: () => ({ navigate: vi.fn(), to: "/" }),
		routeIncidentManagementSource: () => ({ navigate: vi.fn() }),
		routeUser: () => ({ navigate: vi.fn(), to: "/" })
	})
}))

// The overview's lazily loaded parts: replaced, so none finishes loading after the test.
vi.mock("../AlertCreateCaseButton.vue", () => ({ __esModule: true, default: { render: () => null } }))
vi.mock("../AlertSendToChannelButton.vue", () => ({ __esModule: true, default: { render: () => null } }))
vi.mock("../AlertMergeCaseButton.vue", () => ({ __esModule: true, default: { render: () => null } }))
vi.mock("../AlertExclusionRules.vue", () => ({ __esModule: true, default: { render: () => null } }))
vi.mock("../AlertLinkedCases.vue", () => ({ __esModule: true, default: { render: () => null } }))
vi.mock("../AlertUbaLink.vue", () => ({ __esModule: true, default: { render: () => null } }))
vi.mock("../AlertAsset.vue", () => ({ __esModule: true, default: { render: () => null } }))

// The pickers wrap their trigger: render the slot, nothing else.
const slotOnly = defineComponent({
	setup:
		(_, { slots }) =>
		() =>
			h("div", slots.default?.({ loading: false }))
})

const alert = {
	id: 7,
	alert_name: "Malware detected by EDR",
	alert_description: "",
	alert_creation_time: new Date("2026-11-02T12:30:00Z"),
	status: "OPEN",
	source: "crowdstrike",
	customer_code: "ACME",
	assigned_to: null,
	severity: "Critical",
	verdict: null,
	verdict_reason: null,
	verdict_note: null,
	verdict_by: null,
	verdict_at: null,
	time_closed: null,
	comments: [],
	assets: [],
	tags: [],
	linked_cases: [],
	iocs: []
} as unknown as Alert

const stubs = {
	CustomerQuestionBadge: true,
	CustomerQuestionsPanel: true,
	ItemSlaPanel: true,
	AlertDetails: true,
	AlertTimeline: true,
	AlertTags: true,
	EntityDetailsButton: true,
	AlertStatusSwitch: slotOnly,
	AlertVerdictSwitch: slotOnly,
	AlertAssignUser: slotOnly
}

function mountIn(component: unknown, props: Record<string, unknown>) {
	return mount(
		defineComponent({
			setup: () => () =>
				h(NMessageProvider, null, {
					default: () => h(NDialogProvider, null, { default: () => h(component as never, props) })
				})
		}),
		{ global: { stubs } }
	)
}

function mountCard(alertData: Alert, compact = false) {
	return mountIn(AlertItem, { alertData, compact })
}

beforeEach(() => {
	setActivePinia(createPinia())
})

describe("alertItem escalation badge", () => {
	it.each([false, true])("shows Escalated on an escalated alert (compact: %s)", async compact => {
		const wrapper = mountCard({ ...alert, escalated: true }, compact)
		await flushPromises()

		const badge = wrapper.find('[data-testid="alert-escalated-badge"]')
		expect(badge.exists()).toBe(true)
		expect(badge.text()).toContain("Escalated")
	})

	it.each([false, true])("shows nothing for an alert that is not escalated (compact: %s)", async compact => {
		const wrapper = mountCard({ ...alert, escalated: false }, compact)
		await flushPromises()

		expect(wrapper.find('[data-testid="alert-escalated-badge"]').exists()).toBe(false)
	})

	it("shows nothing when an older server leaves the flag out", async () => {
		const wrapper = mountCard(alert)
		await flushPromises()

		expect(wrapper.find('[data-testid="alert-escalated-badge"]').exists()).toBe(false)
	})
})

describe("alertOverview escalation notice", () => {
	it("says the alert is escalated above its status, verdict and assignee", async () => {
		const wrapper = mountIn(AlertOverview, { alert: { ...alert, escalated: true } })
		await flushPromises()

		const notice = wrapper.find('[data-testid="alert-escalated-notice"]')
		expect(notice.exists()).toBe(true)
		expect(notice.text()).toContain("Escalated")
	})

	it("says nothing for an alert that is not escalated", async () => {
		const wrapper = mountIn(AlertOverview, { alert: { ...alert, escalated: false } })
		await flushPromises()

		expect(wrapper.find('[data-testid="alert-escalated-notice"]').exists()).toBe(false)
	})
})
