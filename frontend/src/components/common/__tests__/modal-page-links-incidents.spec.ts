import type { RouteRecordRaw } from "vue-router"
import { flushPromises, mount } from "@vue/test-utils"
import { NDialogProvider, NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import { routes } from "@/router/routes"

/**
 * Every entity modal of incident management, customers, notifications, the AI analyst,
 * SIEM alerts and external services carries a header button to the entity's own page:
 * it points at that page and closing the modal is part of following it.
 */

// Any API call answers "success" — the modals' own content is stubbed below.
function apiProxy(): unknown {
	const call = () => Promise.resolve({ data: { success: true } })
	return new Proxy(call, { get: (_target, key) => (key === "then" ? undefined : apiProxy()) })
}
vi.mock("@/api", () => ({ default: apiProxy() }))

// The details shown inside each modal are covered by their own specs.
function stub(name: string) {
  return {
	__esModule: true,
	default: defineComponent({ name, setup: () => () => h("div", { "data-testid": `stub-${name}` }) })
}
}
vi.mock("@/components/incidentManagement/alerts/AlertDetails.vue", () => stub("AlertDetails"))
vi.mock("@/components/incidentManagement/cases/CaseDetails.vue", () => stub("CaseDetails"))
vi.mock("@/components/incidentManagement/alerts/AlertAssetOverview.vue", () => stub("AlertAssetOverview"))
vi.mock("@/components/incidentManagement/exclusionRules/ExclusionRuleOverview.vue", () => stub("ExclusionRuleOverview"))
vi.mock("@/components/incidentManagement/sources/SourceConfigurationDetails.vue", () =>
	stub("SourceConfigurationDetails"))
vi.mock("@/components/customers/CustomerDetails.vue", () => stub("CustomerDetails"))
vi.mock("@/components/customers/healthcheck/CustomerHealthcheckDetails.vue", () =>
	stub("CustomerHealthcheckDetails"))
vi.mock("@/components/customers/aiNotifications/CustomerAiNotificationRoutes/CustomerAiNotificationRouteOverview.vue", () =>
	stub("CustomerAiNotificationRouteOverview"))
vi.mock("@/components/notifications/NotificationTemplateOverview.vue", () => stub("NotificationTemplateOverview"))
vi.mock("@/components/aiAnalyst/AlertReportDetails.vue", () => stub("AlertReportDetails"))
vi.mock("@/components/alerts/AlertDetailTabs.vue", () => stub("AlertDetailTabs"))
vi.mock("@/components/integrations/IntegrationDetails.vue", () => stub("IntegrationDetails"))
vi.mock("@/components/networkConnectors/NetworkConnectorDetails.vue", () => stub("NetworkConnectorDetails"))

/** The app's real route table, with every page blanked: only names and paths matter here. */
function blankRoutes(records: RouteRecordRaw[]): RouteRecordRaw[] {
	return records.map(record => {
		const copy = { ...record } as RouteRecordRaw & { component?: unknown; children?: RouteRecordRaw[] }
		if ("component" in copy && copy.component) copy.component = { render: () => null }
		if (copy.children) copy.children = blankRoutes(copy.children)
		return copy as RouteRecordRaw
	})
}

async function openModal(component: unknown, props: Record<string, unknown>) {
	const router = createRouter({ history: createMemoryHistory(), routes: blankRoutes(routes) })
	await router.push("/")
	await router.isReady()
	const Host = defineComponent({
		setup: () => () =>
			h(NMessageProvider, null, {
				default: () => h(NDialogProvider, null, { default: () => h(component as never, props) })
			})
	})
	const wrapper = mount(Host, { global: { plugins: [router] }, attachTo: document.body })
	await flushPromises()
	wrapper.findComponent(EntityDetailsButton).vm.$emit("view")
	await flushPromises()
	const link = () => document.querySelector<HTMLAnchorElement>("[data-testid=modal-page-button]")
	return { wrapper, router, link }
}

/** Follows the header link and checks the modal went away with the navigation. */
async function follow(opened: Awaited<ReturnType<typeof openModal>>, expectedPath: string) {
	const link = opened.link()
	expect(link?.getAttribute("href")).toBe(expectedPath)
	link?.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, button: 0 }))
	await flushPromises()
	await new Promise(resolve => setTimeout(resolve, 350)) // the modal's leave transition
	expect(opened.router.currentRoute.value.fullPath).toBe(expectedPath)
	expect(opened.link()).toBeNull()
}

beforeEach(() => setActivePinia(createPinia()))
afterEach(() => {
	document.body.innerHTML = ""
})

describe("entity modals link to the entity's page", () => {
	it("an incident alert", async () => {
		const { default: AlertItem } = await import("@/components/incidentManagement/alerts/AlertItem.vue")
		const alert = {
			id: 42,
			alert_name: "Brute force",
			alert_description: "",
			status: "OPEN",
			customer_code: "ACME",
			source: "wazuh",
			assigned_to: null,
			alert_creation_time: "2026-09-01T08:00:00",
			time_closed: null,
			comments: [],
			assets: [],
			cases: [],
			linked_cases: [], // present, so the item renders this alert instead of fetching it
			tags: [],
			iocs: []
		}
		await follow(await openModal(AlertItem, { alertData: alert, compact: true }), "/incident-management/alerts/42")
	})

	it("an incident case", async () => {
		const { default: CaseItem } = await import("@/components/incidentManagement/cases/CaseItem.vue")
		const caseEntity = {
			id: 7,
			case_name: "Investigation",
			case_description: "",
			case_status: "OPEN",
			customer_code: "ACME",
			assigned_to: null,
			case_creation_time: "2026-09-01T08:00:00",
			alerts: []
		}
		await follow(await openModal(CaseItem, { caseData: caseEntity }), "/incident-management/cases/7")
	})

	it("an alert asset", async () => {
		const { default: AlertAsset } = await import("@/components/incidentManagement/alerts/AlertAsset.vue")
		const asset = {
			id: 5,
			alert_linked: 42,
			asset_name: "host-1",
			agent_id: "001",
			customer_code: "ACME",
			index_id: "abc",
			index_name: "wazuh-alerts-1",
			velociraptor_id: "",
			velociraptor_org: ""
		}
		await follow(await openModal(AlertAsset, { asset }), "/incident-management/alerts/42/assets/5")
	})

	it("the SIEM alert behind an asset", async () => {
		const { default: AlertAssetInfo } = await import("@/components/incidentManagement/alerts/AlertAssetInfo.vue")
		const asset = {
			id: 5,
			alert_linked: 42,
			asset_name: "host-1",
			agent_id: "001",
			customer_code: "ACME",
			index_id: "evt-1",
			index_name: "wazuh-alerts-1"
		}
		await follow(await openModal(AlertAssetInfo, { asset }), "/alerts/siem/alert/wazuh-alerts-1/evt-1")
	})

	it("an exclusion rule", async () => {
		const { default: ExclusionRuleItem } = await import(
			"@/components/incidentManagement/exclusionRules/ExclusionRuleItem.vue"
		)
		const entity = { id: 9, name: "Noisy rule", enabled: true, customer_code: null, source_alert_id: null }
		await follow(await openModal(ExclusionRuleItem, { entity }), "/incident-management/exclusion-rules/9")
	})

	it("a configured source", async () => {
		const { default: ConfiguredSourceItem } = await import(
			"@/components/incidentManagement/sources/ConfiguredSourceItem.vue"
		)
		await follow(await openModal(ConfiguredSourceItem, { source: "wazuh" }), "/incident-management/sources/wazuh")
	})

	it("a customer", async () => {
		const { default: CustomerItem } = await import("@/components/customers/CustomerItem.vue")
		const customer = { customer_code: "ACME", customer_name: "Acme Corp", contact_first_name: "", contact_last_name: "" }
		await follow(await openModal(CustomerItem, { customer }), "/customers/ACME")
	})

	it("an agent's health check", async () => {
		const { default: CustomerHealthcheckItem } = await import(
			"@/components/customers/healthcheck/CustomerHealthcheckItem.vue"
		)
		const healthData = {
			id: 1,
			label: "host-1",
			agent_id: "001",
			os: "linux",
			last_seen: "2026-09-01T08:00:00",
			unhealthy_reason: null
		}
		await follow(
			await openModal(CustomerHealthcheckItem, { healthData, source: "wazuh", customerCode: "ACME" }),
			"/customers/ACME/healthcheck/wazuh/001"
		)
	})

	it("an internal notification route — and no link for a customer route, which has no page", async () => {
		const { default: RouteItem } = await import(
			"@/components/customers/aiNotifications/CustomerAiNotificationRoutes/CustomerAiNotificationRouteItem.vue"
		)
		const route = {
			id: 3,
			name: "SOC Teams",
			trigger: "sla_breached",
			channel: "teams",
			enabled: true,
			min_severity: "High",
			customer_code: null,
			config: {}
		}
		await follow(await openModal(RouteItem, { route, scope: "internal" }), "/internal-notifications/3")

		document.body.innerHTML = ""
		const customerScoped = await openModal(RouteItem, {
			route: { ...route, customer_code: "ACME" },
			customerCode: "ACME",
			scope: "customer"
		})
		expect(document.body.textContent).toContain("#3 • SOC Teams") // the modal is open…
		expect(customerScoped.link()).toBeNull() // …without a page to offer
	})

	it("a message template", async () => {
		const { default: NotificationTemplateItem } = await import("@/components/notifications/NotificationTemplateItem.vue")
		const template = {
			id: 11,
			name: "SLA — running late",
			format: "markdown",
			is_default: true,
			trigger: null,
			body_template: "*SLA breached*"
		}
		await follow(await openModal(NotificationTemplateItem, { template }), "/message-templates/11")
	})

	it("an AI analyst report", async () => {
		const { default: AlertReportItem } = await import("@/components/aiAnalyst/AlertReportItem.vue")
		const alertData = {
			alert_id: 42,
			alert_name: "Brute force",
			customer_code: "ACME",
			report: { id: 77, severity_assessment: "High", created_at: "2026-09-01T08:00:00" }
		}
		await follow(await openModal(AlertReportItem, { alertData }), "/ai-analyst/reports/77")
	})

	it("a SIEM alert", async () => {
		const { default: SiemAlert } = await import("@/components/alerts/Alert.vue")
		const alert = { _id: "evt-1", _index: "wazuh-alerts-1", _source: { id: "evt-1", rule_description: "x" } }
		await follow(await openModal(SiemAlert, { alert }), "/alerts/siem/alert/wazuh-alerts-1/evt-1")
	})

	it("a third-party integration and a network connector", async () => {
		const { default: ServiceItem } = await import("@/components/services/Item.vue")
		const data = { id: 4, name: "Huntress", description: "", auth_keys: [] }
		await follow(await openModal(ServiceItem, { data, type: "integration" }), "/external-services/third-party-integrations/4")
		document.body.innerHTML = ""
		await follow(
			await openModal(ServiceItem, { data, type: "network-connector" }),
			"/external-services/network-connectors/4"
		)
	})
})
