import type { AttentionItem, Compliance, ItemSla } from "@/types/soc-management"
import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import AttentionList from "../AttentionList.vue"
import ItemSlaPanel from "../ItemSlaPanel.vue"
import ComplianceMeter from "../ui/ComplianceMeter.vue"
import DeltaChip from "../ui/DeltaChip.vue"
import KpiTile from "../ui/KpiTile.vue"
import LoadBars from "../ui/LoadBars.vue"
import SlaGauge from "../ui/SlaGauge.vue"
import SlaStateTag from "../ui/SlaStateTag.vue"

const getItemSla = vi.fn()
vi.mock("@/api", () => ({ default: { socManagement: { getItemSla: (...args: unknown[]) => getItemSla(...args) } } }))

/** RouterLink without a router: render the target as data so the test can read it. */
const RouterLinkStub = defineComponent({
	props: { to: { type: Object, required: true } },
	setup(props, { slots }) {
		return () => h("a", { "data-to": JSON.stringify(props.to) }, slots.default?.())
	}
})

function compliance(over: Partial<Compliance> = {}): Compliance {
	return { met: 0, breached: 0, at_risk: 0, on_track: 0, paused: 0, not_tracked: 0, decided: 0, rate: null, ...over }
}

beforeEach(() => {
	setActivePinia(createPinia())
	getItemSla.mockReset()
})

describe("complianceMeter", () => {
	it("prints the rate and fills the meter to it", () => {
		const wrapper = mount(ComplianceMeter, {
			props: { compliance: compliance({ met: 19, breached: 1, decided: 20, rate: 95 }) }
		})
		expect(wrapper.text()).toContain("95.0%")
		const meter = wrapper.get("[role=meter]")
		expect(meter.attributes("aria-valuenow")).toBe("95")
		expect(wrapper.get(".meter-fill").attributes("style")).toContain("width: 95%")
	})

	it("reads 'no outcome yet' as a dash, never as 0%", () => {
		const wrapper = mount(ComplianceMeter, { props: { compliance: compliance() } })
		expect(wrapper.text()).toContain("—")
		expect(wrapper.text()).not.toContain("0.0%")
		expect(wrapper.get("[role=meter]").attributes("aria-valuenow")).toBeUndefined()
	})
})

describe("kpiTile and deltaChip", () => {
	it("renders label, value, hint and the delta vs the previous period", () => {
		const wrapper = mount(KpiTile, {
			props: {
				label: "Alerts opened",
				value: "1,284",
				hint: "120 resolved",
				delta: { label: "+12%", direction: "up", tone: "neutral" }
			}
		})
		expect(wrapper.text()).toContain("Alerts opened")
		expect(wrapper.get("[data-testid=kpi-value]").text()).toBe("1,284")
		expect(wrapper.get("[data-testid=delta-chip]").text()).toContain("+12%")
		expect(wrapper.text()).toContain("120 resolved")
	})

	it("colours the value only when it is a status", () => {
		const plain = mount(KpiTile, { props: { label: "x", value: "3" } })
		expect(plain.get("[data-testid=kpi-value]").attributes("style") ?? "").not.toContain("color")
		const bad = mount(KpiTile, { props: { label: "Past SLA", value: "3", tone: "bad" } })
		expect(bad.get("[data-testid=kpi-value]").attributes("style")).toContain("var(--error-color)")
	})

	it("renders no chip without a delta", () => {
		expect(
			mount(DeltaChip, { props: { delta: null } })
				.find("[data-testid=delta-chip]")
				.exists()
		).toBe(false)
	})
})

describe("slaGauge", () => {
	it("shows the rate with its objective in the accessible name", () => {
		const wrapper = mount(SlaGauge, { props: { rate: 96.4, label: "Resolved in SLA" } })
		expect(wrapper.get("[data-testid=sla-gauge-value]").text().replace(/\s/g, "")).toBe("96.4%")
		expect(wrapper.get("svg").attributes("aria-label")).toBe("Resolved in SLA: 96.4%, objective 95%")
	})

	it("draws no arc and shows a dash when there is no rate", () => {
		const wrapper = mount(SlaGauge, { props: { rate: null, label: "Resolved in SLA" } })
		expect(wrapper.find(".gauge-arc").exists()).toBe(false)
		expect(wrapper.get("[data-testid=sla-gauge-value]").text()).toBe("—")
	})
})

describe("slaStateTag", () => {
	it("pairs every state with a word, so colour never travels alone", () => {
		expect(mount(SlaStateTag, { props: { state: "breached" } }).text()).toBe("Breached")
		expect(mount(SlaStateTag, { props: { state: "at_risk" } }).text()).toBe("At risk")
		expect(mount(SlaStateTag, { props: { state: "met", label: "Response met" } }).text()).toBe("Response met")
	})
})

describe("attentionList", () => {
	const item = (over: Partial<AttentionItem>): AttentionItem => ({
		entity: "alert",
		id: 7,
		title: "Brute force",
		customer_code: "ACME",
		severity: "High",
		status: "OPEN",
		assigned_to: null,
		opened_at: "2026-09-01T08:00:00",
		state: "breached",
		clock: "ack",
		due_at: "2026-09-01T09:00:00",
		overdue_seconds: 7500,
		...over
	})

	it("links each row to its alert or case and says how late it is", () => {
		const wrapper = mount(AttentionList, {
			props: {
				items: [
					item({}),
					item({ entity: "case", id: 3, state: "at_risk", clock: "resolve", overdue_seconds: -2100 })
				]
			},
			global: { stubs: { RouterLink: RouterLinkStub } }
		})
		const links = wrapper.findAll("a")
		expect(JSON.parse(links[0].attributes("data-to") as string)).toEqual({
			name: "IncidentManagement-Alert",
			params: { id: "7" }
		})
		expect(JSON.parse(links[1].attributes("data-to") as string)).toEqual({
			name: "IncidentManagement-Case",
			params: { id: "3" }
		})
		expect(wrapper.text()).toContain("ALERT-7")
		expect(wrapper.text()).toContain("Response breached")
		expect(wrapper.text()).toContain("2h 05m late")
		expect(wrapper.text()).toContain("Resolution at risk")
		expect(wrapper.text()).toContain("35m left")
		expect(wrapper.text()).toContain("unassigned")
	})

	it("says so when nothing needs attention", () => {
		const wrapper = mount(AttentionList, {
			props: { items: [] },
			global: { stubs: { RouterLink: RouterLinkStub } }
		})
		expect(wrapper.text()).toContain("Nothing open is past or close to its SLA")
	})
})

describe("loadBars", () => {
	it("scales every bar against the largest row and prints the counts beside it", () => {
		const wrapper = mount(LoadBars, {
			props: {
				rows: [
					{ key: "ana", label: "ana", alerts: 6, cases: 2, at_risk: 1, breached: 3 },
					{ key: "bob", label: "bob", alerts: 4, cases: 0, at_risk: 0, breached: 0 }
				]
			}
		})
		const ana = wrapper.get("[data-testid=load-row-ana]")
		const segments = ana.findAll(".bar-segment")
		expect(segments[0].attributes("style")).toContain("width: 75%")
		expect(segments[1].attributes("style")).toContain("width: 25%")
		expect(ana.text()).toContain("8")
		expect(ana.get("[title='3 past SLA']").text()).toBe("3")
		expect(wrapper.get("[data-testid=load-row-bob]").findAll(".bar-segment")).toHaveLength(1)
	})
})

describe("itemSlaPanel", () => {
	const sla: ItemSla = {
		entity: "alert",
		id: 7,
		severity: "High",
		opened_at: "2026-09-01T08:00:00",
		tracked: true,
		ack: {
			due_at: "2026-09-01T09:00:00",
			achieved_at: "2026-09-01T08:12:00",
			state: "met",
			by: "ana",
			action: "assigned",
			target_minutes: 60
		},
		resolve: {
			due_at: "2026-09-01T16:00:00",
			achieved_at: null,
			state: "on_track",
			by: null,
			action: null,
			target_minutes: 480
		},
		first_assigned_at: "2026-09-01T08:12:00",
		reopen_count: 1,
		business_hours: false,
		calendar_timezone: null,
		paused_at: null,
		paused_seconds: 0,
		generated_at: "2026-09-01T10:00:00"
	}

	it("shows both clocks: time used against the target, and who stopped them", async () => {
		getItemSla.mockResolvedValue({ data: sla })
		const wrapper = mount(ItemSlaPanel, { props: { entity: "alert", itemId: 7 } })
		await flushPromises()
		expect(getItemSla).toHaveBeenCalledWith("alert", 7, expect.any(AbortSignal))
		expect(wrapper.get("[data-testid=item-sla-ack]").text()).toContain("12m of 1h · ana")
		expect(wrapper.get("[data-testid=item-sla-resolve]").text()).toContain("6h left of 8h")
		expect(wrapper.get("[data-testid=item-sla-resolve] [role=progressbar]").attributes("aria-valuenow")).toBe("25")
		expect(wrapper.text()).toContain("reopened 1×")
		expect(wrapper.emitted("loaded")?.[0]).toEqual([sla])
	})

	it("shows a paused item as waiting on the customer, its clocks stopped where they were", async () => {
		getItemSla.mockResolvedValue({
			data: {
				...sla,
				paused_at: "2026-09-01T10:00:00",
				paused_seconds: 3600,
				generated_at: "2026-09-01T11:00:00",
				resolve: { ...sla.resolve, state: "paused" }
			}
		})
		const wrapper = mount(ItemSlaPanel, { props: { entity: "alert", itemId: 7 } })
		await flushPromises()
		expect(wrapper.get("[data-testid=item-sla-paused]").text()).toContain("Waiting on customer")
		expect(wrapper.get("[data-testid=item-sla-resolve]").text()).toContain("Waiting on customer")
		expect(wrapper.get("[data-testid=item-sla-resolve]").text()).toContain("stopped · 8h target")
		// Frozen at the pause (2h of 8h), not at "now" (3h).
		expect(wrapper.get("[data-testid=item-sla-resolve] [role=progressbar]").attributes("aria-valuenow")).toBe("25")
	})

	it("states business hours and gives a due time rather than a wall-clock countdown", async () => {
		getItemSla.mockResolvedValue({
			data: { ...sla, business_hours: true, calendar_timezone: "Europe/Rome", paused_seconds: 5400 }
		})
		const wrapper = mount(ItemSlaPanel, { props: { entity: "alert", itemId: 7 } })
		await flushPromises()
		expect(wrapper.get("[data-testid=item-sla-business-hours]").text()).toContain("Europe/Rome")
		expect(wrapper.get("[data-testid=item-sla-resolve]").text()).toMatch(/due .* · 8h working/)
		expect(wrapper.get("[data-testid=item-sla-waited]").text()).toContain("waited 1h 30m")
	})

	it("explains an untracked item instead of inventing a clock", async () => {
		getItemSla.mockResolvedValue({ data: { ...sla, tracked: false } })
		const wrapper = mount(ItemSlaPanel, { props: { entity: "case", itemId: 3 } })
		await flushPromises()
		expect(wrapper.text()).toContain("opened before SLA tracking began")
		expect(wrapper.find("[data-testid=item-sla-ack]").exists()).toBe(false)
	})

	it("hides itself when the caller may not read SLA data", async () => {
		getItemSla.mockImplementation(() =>
			Promise.reject(Object.assign(new Error("Forbidden"), { response: { status: 403 } }))
		)
		const wrapper = mount(ItemSlaPanel, { props: { entity: "alert", itemId: 7 } })
		await flushPromises()
		expect(wrapper.html()).toBe("<!--v-if-->")
		expect(wrapper.emitted("loaded")?.[0]).toEqual([null])
	})

	it("reloads when the item changes", async () => {
		getItemSla.mockResolvedValue({ data: sla })
		const wrapper = mount(ItemSlaPanel, { props: { entity: "alert", itemId: 7, refreshKey: "OPEN" } })
		await flushPromises()
		await wrapper.setProps({ refreshKey: "CLOSED" })
		await flushPromises()
		expect(getItemSla).toHaveBeenCalledTimes(2)
	})
})
