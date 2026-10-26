import type { OverviewTrend } from "@/types/portal"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick } from "vue"
import i18n from "@/lang"
import { buildPostureCells } from "../posture/postureCells"
import OverviewTrendChart from "../trend/OverviewTrendChart.vue"
import OverviewTrendPanel from "../trend/OverviewTrendPanel.vue"
import { trendDays } from "../trend/trend"

vi.mock("vue-echarts", () => ({
	default: defineComponent({ name: "VChart", props: { option: Object }, setup: () => () => h("div") })
}))

const TREND: OverviewTrend = {
	range: "7d",
	since: "2026-10-09T10:00:00Z",
	until: "2026-10-17T10:00:00Z",
	hours: [{ hour: "2026-10-15T10:00:00Z", alerts_opened: 4, alerts_closed: 1, cases_opened: 0, cases_closed: 0 }],
	alerts_open_at_since: 3,
	cases_open_at_since: 0,
	alerts_error: null,
	cases_error: null
}

beforeEach(() => setActivePinia(createPinia()))

/** The Overview follows the user's language (#1310). */
describe("overview i18n", () => {
	it("shows the trend panel in Italian", () => {
		i18n.global.locale.value = "it"
		const wrapper = mount(OverviewTrendPanel, {
			props: { trend: TREND, days: trendDays(TREND), range: "7d", loading: false, error: null }
		})
		expect(wrapper.text()).toContain("Andamento")
		expect(wrapper.text()).toContain("ultimi 7 giorni")
		expect(wrapper.get("[data-testid=overview-trend-open-caption]").text()).toBe("ancora aperti · prima 3")
		expect(wrapper.get("[data-testid=overview-trend-table] thead").text()).toContain("Aperti a fine giornata")
	})

	it("redraws the chart's texts when the language changes", async () => {
		i18n.global.locale.value = "it"
		const wrapper = mount(OverviewTrendChart, { props: { days: trendDays(TREND), entity: "alerts" } })
		const axisNames = () =>
			(wrapper.getComponent({ name: "VChart" }).props("option") as { yAxis: { name: string }[] }).yAxis.map(
				axis => axis.name
			)
		expect(axisNames()).toEqual(["Aperti · a fine giornata", "Nuovi ↑  Chiusi ↓"])

		i18n.global.locale.value = "de"
		await nextTick()
		expect(axisNames()).toEqual(["Offen · am Tagesende", "Neu ↑  Geschlossen ↓"])
	})

	it("agrees the posture labels with their counts", () => {
		i18n.global.locale.value = "it"
		const counts = { total: 4, open: 1, in_progress: 0, pending_customer: 0, closed: 3 }
		const [alerts] = buildPostureCells({
			alerts: counts,
			cases: counts,
			agents: { total: 1, online: 1, offline: 0, critical: 0 }
		})
		expect(alerts!.caption).toBe("alert aperto")
		expect(alerts!.segments.map(segment => segment.label)).toEqual(["aperto", "in corso", "in attesa di te", "chiusi"])
	})
})
