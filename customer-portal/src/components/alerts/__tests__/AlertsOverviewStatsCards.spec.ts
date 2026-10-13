import type { AlertStatus } from "@/types/alerts"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import AlertsOverviewStatsCards from "../AlertsOverviewStatsCards.vue"

const alertsStats = vi.hoisted(() => vi.fn())
vi.mock("@/api", () => ({ default: { portal: { alertsStats } } }))

function mountCards(status: AlertStatus | null) {
	const updates: (AlertStatus | null)[] = []
	const wrapper = mount(
		defineComponent({
			setup: () => () =>
				h(NMessageProvider, null, () =>
					h(AlertsOverviewStatsCards, { "status": status, "onUpdate:status": (value: AlertStatus | null) => updates.push(value) }))
		})
	)
	return { wrapper, updates }
}

/** The status cards set the list's status filter (#1245). */
describe("alerts status cards", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		alertsStats.mockResolvedValue({ data: { total: 6, open: 3, in_progress: 1, pending_customer: 1, closed: 1 } })
	})

	it("marks the card of the status in force", async () => {
		const { wrapper } = mountCards("PENDING_CUSTOMER")
		await flushPromises()
		expect(wrapper.get("[data-testid=stat-pending_customer]").attributes("aria-pressed")).toBe("true")
		expect(wrapper.get("[data-testid=stat-total]").attributes("aria-pressed")).toBe("false")
	})

	it("sets the status a card stands for, and the total clears it", async () => {
		const { wrapper, updates } = mountCards(null)
		await flushPromises()
		await wrapper.get("[data-testid=stat-in_progress]").trigger("click")
		await wrapper.get("[data-testid=stat-total]").trigger("click")
		expect(updates).toEqual(["IN_PROGRESS", null])
	})
})
