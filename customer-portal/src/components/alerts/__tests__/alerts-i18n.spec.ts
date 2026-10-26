import type { AlertsFilters } from "@/components/alerts/filters/alertsFilters"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick } from "vue"
import { EMPTY_ALERTS_FILTERS, openedLabel } from "@/components/alerts/filters/alertsFilters"
import i18n from "@/lang"
import AlertsFilterBar from "../filters/AlertsFilterBar.vue"

const getAlertsFilters = vi.hoisted(() => vi.fn())
const searchAlertAssets = vi.hoisted(() => vi.fn())
vi.mock("@/api", () => ({ default: { alerts: { getAlertsFilters, searchAlertAssets } } }))

function mountBar(filters: Partial<AlertsFilters>) {
	return mount(
		defineComponent({
			setup: () => () =>
				h(NMessageProvider, null, () => h(AlertsFilterBar, { filters: { ...EMPTY_ALERTS_FILTERS, ...filters } }))
		})
	)
}

/** The alerts area follows the user's language (#1310). */
describe("the alerts area in Italian", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		getAlertsFilters.mockResolvedValue({ data: { sources: [], tags: [], statuses: [], assets: [] } })
		searchAlertAssets.mockResolvedValue({ data: { assets: [] } })
	})

	it("names the filters, their buttons and the link-only chips in Italian", async () => {
		i18n.global.locale.value = "it"
		const wrapper = mountBar({ source: "wazuh", openedFrom: "2026-09-01T12:00:00Z" })
		await flushPromises()

		expect(wrapper.get("[data-testid=alerts-filter-source]").text()).toContain("Origine")
		expect(wrapper.get("[data-testid=alerts-filter-opened]").text()).toContain("Arrivato al SOC")
		expect(wrapper.get("[data-testid=alerts-filter-opened-value]").text()).toMatch(/^dal /)
		expect(wrapper.get("[data-testid=alerts-filter-source-remove]").attributes("aria-label")).toBe(
			"Rimuovi il filtro per origine"
		)
		expect(wrapper.get("[data-testid=alerts-filter-clear]").text()).toBe("Rimuovi i filtri")
	})

	it("switches language while shown", async () => {
		const wrapper = mountBar({ source: "wazuh" })
		await flushPromises()
		expect(wrapper.get("[data-testid=alerts-filter-add]").text()).toBe("Add filter")

		i18n.global.locale.value = "it"
		await nextTick()
		expect(wrapper.get("[data-testid=alerts-filter-add]").text()).toBe("Aggiungi filtro")
	})

	it("words a helper's label in the language in force when it is asked", () => {
		const filters = { ...EMPTY_ALERTS_FILTERS, openedBefore: "2026-10-01T12:00:00Z" }
		expect(openedLabel(filters, () => "01/10")).toBe("before 01/10")
		i18n.global.locale.value = "it"
		expect(openedLabel(filters, () => "01/10")).toBe("prima del 01/10")
	})
})
