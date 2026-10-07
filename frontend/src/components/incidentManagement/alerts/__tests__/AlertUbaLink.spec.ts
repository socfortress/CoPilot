import type { RouteRecordRaw } from "vue-router"
import type { Alert } from "@/types/incidentManagement/alerts"
import { flushPromises, mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { createMemoryHistory, createRouter } from "vue-router"
import { ubaRoutes } from "@/router/routes/uba"
import AlertUbaLink from "../AlertUbaLink.vue"

const getAlertContext = vi.fn()

vi.mock("@/api", () => ({
	default: { incidentManagement: { alerts: { getAlertContext: (...a: unknown[]) => getAlertContext(...a) } } }
}))

const UBA_CONTEXT = {
	uba_alert_id: "72cdf138-8f0a-57c6-a066-6832e03dfc98",
	uba_entity_key: "windows-demo\\jdoe",
	uba_entity_name: "WINDOWS-DEMO\\jdoe"
}

function alertOf(source: string): Alert {
	return {
		id: 6647,
		source,
		customer_code: "ACME",
		assets: [{ id: 1, alert_context_id: 326 }]
	} as unknown as Alert
}

async function render(source = "uba") {
	const router = createRouter({
		history: createMemoryHistory(),
		routes: [
			...(ubaRoutes.map(r => (r.redirect ? r : { ...r, component: { render: () => null } })) as RouteRecordRaw[]),
			{ path: "/", component: { render: () => null } }
		]
	})
	await router.push("/")
	const wrapper = mount(AlertUbaLink, { props: { alert: alertOf(source) }, global: { plugins: [router] } })
	await flushPromises()
	return { wrapper, router }
}

describe("alertUbaLink", () => {
	beforeEach(() => {
		getAlertContext
			.mockReset()
			.mockResolvedValue({ data: { success: true, alert_context: { context: UBA_CONTEXT } } })
	})

	it("links the UBA alert and the entity to their pages", async () => {
		const { wrapper } = await render()
		expect(getAlertContext).toHaveBeenCalledWith(326)
		expect(wrapper.get("[data-testid=alert-uba-alert-link]").attributes("href")).toBe(
			"/uba/ACME/alerts/72cdf138-8f0a-57c6-a066-6832e03dfc98"
		)
		const entity = wrapper.get("[data-testid=alert-uba-entity-link]")
		expect(entity.attributes("href")).toBe("/uba/ACME/entities/windows-demo%5Cjdoe")
		expect(entity.text()).toContain("WINDOWS-DEMO\\jdoe")
	})

	it("navigates in the app on a plain click and leaves a modified click to the browser", async () => {
		const { wrapper, router } = await render()
		await wrapper.get("[data-testid=alert-uba-alert-link]").trigger("click", { metaKey: true })
		await flushPromises()
		expect(router.currentRoute.value.path).toBe("/")
		await wrapper.get("[data-testid=alert-uba-entity-link]").trigger("click")
		await flushPromises()
		expect(router.currentRoute.value.name).toBe("UbaEntity")
		expect(router.currentRoute.value.params.entityKey).toBe("windows-demo\\jdoe")
	})

	it("stays out of alerts from other sources", async () => {
		const { wrapper } = await render("wazuh")
		expect(getAlertContext).not.toHaveBeenCalled()
		expect(wrapper.find("[data-testid=alert-uba-alert-link]").exists()).toBe(false)
	})
})
