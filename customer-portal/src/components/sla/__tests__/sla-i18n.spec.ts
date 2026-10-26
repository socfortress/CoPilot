import type { SlaTarget } from "@/types/sla"
import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import { nextTick } from "vue"
import i18n from "@/lang"
import { formatDuration, groupTargets, PERIOD_PRESETS } from "../sla"
import SlaTargetsTable from "../SlaTargetsTable.vue"

const targets: SlaTarget[] = [
	{
		entity: "alert",
		severity: "Critical",
		acknowledge_minutes: 15,
		resolve_minutes: 240,
		business_hours: true,
		opened: 4,
		acknowledge_rate: 100,
		resolve_rate: 75,
		time_to_resolve: 3600
	},
	{
		entity: "alert",
		severity: "Low",
		acknowledge_minutes: 480,
		resolve_minutes: null,
		business_hours: false,
		opened: 0,
		acknowledge_rate: null,
		resolve_rate: null,
		time_to_resolve: null
	}
]

/** The Service Levels page follows the user's language (#1310). */
describe("the SLA page in Italian", () => {
	it("shows the promise table in Italian, severities included", () => {
		i18n.global.locale.value = "it"
		const wrapper = mount(SlaTargetsTable, { props: { groups: groupTargets(targets) } })

		expect(wrapper.text()).toContain("Gravità")
		expect(wrapper.text()).toContain("Risposta")
		expect(wrapper.text()).toContain("Rispettato")
		expect(wrapper.get("[data-testid=sla-target-alert-critical]").text()).toContain("Critica")
		expect(wrapper.get("[data-testid=sla-target-alert-critical]").text()).toContain("orario lavorativo")
		expect(wrapper.get("[data-testid=sla-target-alert-low]").text()).toContain("Nessun obiettivo")
		expect(wrapper.text()).not.toContain("Resolution")
	})

	it("switches language without a reload", async () => {
		const wrapper = mount(SlaTargetsTable, { props: { groups: groupTargets(targets) } })
		expect(wrapper.text()).toContain("Response")

		i18n.global.locale.value = "it"
		await nextTick()
		expect(wrapper.text()).toContain("Risposta")
	})

	it("writes durations and periods in Italian", () => {
		i18n.global.locale.value = "it"
		expect(formatDuration(2 * 86_400 + 4 * 3600)).toBe("2g 4h")
		expect(PERIOD_PRESETS.map(preset => preset.label)).toEqual(["7 giorni", "30 giorni", "90 giorni"])
	})
})
