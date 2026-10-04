import type { BusinessCalendar } from "@/types/soc-management"
import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick, ref, shallowRef } from "vue"
import { useAttention } from "../composables/useAttention"
import { useBusinessCalendar } from "../composables/useBusinessCalendar"
import HolidayList from "../policies/HolidayList.vue"
import SegmentedPanel from "../ui/SegmentedPanel.vue"
import SeverityTag from "../ui/SeverityTag.vue"
import SocPanel from "../ui/SocPanel.vue"
import Sparkline from "../ui/Sparkline.vue"
import { SEVERITY_TONE } from "../utils"
import { CALENDAR } from "./fixtures"

const api = { getAttention: vi.fn(), getCalendar: vi.fn(), saveCalendar: vi.fn(), deleteCalendar: vi.fn() }
const sparkOptions: unknown[] = []
vi.mock("vue-echarts", () => ({
	default: defineComponent({
		props: { option: { type: Object, required: true } },
		setup(props) {
			return () => {
				sparkOptions.push(props.option)
				return h("div", { "data-testid": "v-chart" })
			}
		}
	})
}))

vi.mock("@/api", () => ({
	default: {
		socManagement: new Proxy(
			{},
			{ get: (_, name: string) => (...args: unknown[]) => api[name as keyof typeof api](...args) }
		)
	}
}))

/** Runs a composable inside a component, so its watchers live as they would on a page. */
function withSetup<T>(composable: () => T): T {
	let result!: T
	mount(
		defineComponent({
			setup() {
				result = composable()
				return () => h("div")
			}
		})
	)
	return result
}

function deferred<T>() {
	let resolve!: (value: T) => void
	const promise = new Promise<T>(r => {
		resolve = r
	})
	return { promise, resolve }
}

beforeEach(() => {
	setActivePinia(createPinia())
	for (const mock of Object.values(api)) mock.mockReset()
})

describe("useAttention", () => {
	it("loads with scope, filter and the page limit, and reloads when they change", async () => {
		api.getAttention.mockResolvedValue({ data: { items: [{ id: 1 }], total: 7 } })
		const scope = ref({ customerCodes: ["ACME"] })
		const filter = ref<{ entity?: "alert" | "case" }>({})
		const attention = withSetup(() => useAttention(scope, filter))
		await flushPromises()
		expect(api.getAttention).toHaveBeenCalledWith({ customerCodes: ["ACME"], limit: 200 }, expect.any(AbortSignal))
		expect([attention.items.value.length, attention.total.value, attention.loading.value]).toEqual([1, 7, false])
		filter.value = { entity: "case" }
		await flushPromises()
		expect(api.getAttention).toHaveBeenLastCalledWith({ customerCodes: ["ACME"], entity: "case", limit: 200 }, expect.any(AbortSignal))
	})

	it("aborts the load it supersedes and keeps only the latest answer", async () => {
		const first = deferred<unknown>()
		api.getAttention.mockReturnValueOnce(first.promise).mockResolvedValueOnce({ data: { items: [{ id: 2 }], total: 1 } })
		const filter = ref({})
		const attention = withSetup(() => useAttention(ref({}), filter))
		filter.value = { state: "breached" }
		await flushPromises()
		const firstSignal = api.getAttention.mock.calls[0][1] as AbortSignal
		expect(firstSignal.aborted).toBe(true)
		first.resolve({ data: { items: [{ id: 1 }], total: 1 } })
		await flushPromises()
		expect(attention.items.value).toEqual([{ id: 2 }])
	})

	it("reports a failure but not a cancellation", async () => {
		api.getAttention.mockImplementationOnce(() => Promise.reject(Object.assign(new Error("x"), { name: "CanceledError" })))
		const attention = withSetup(() => useAttention(ref({}), ref({})))
		await flushPromises()
		expect(attention.error.value).toBeNull()
		api.getAttention.mockImplementationOnce(() => Promise.reject(new Error("down")))
		await attention.reload()
		expect((attention.error.value as Error | null)?.message).toBe("down")
	})
})

describe("useBusinessCalendar", () => {
	const own: BusinessCalendar = { ...CALENDAR, customer_code: "ACME", source: "customer", timezone: "Europe/Rome" }

	function respond(calendar: BusinessCalendar, customers: string[] = []) {
		return { data: { calendar, customers_with_calendar: customers, retargeted: 0, message: "ok" } }
	}

	it("loads the scope's calendar and says whether the customer has one of its own", async () => {
		api.getCalendar.mockResolvedValueOnce(respond(CALENDAR, ["GLOBEX"]))
		const scope = shallowRef<string | null>("ACME")
		const calendar = withSetup(() => useBusinessCalendar(scope))
		await flushPromises()
		expect(api.getCalendar).toHaveBeenCalledWith("ACME")
		expect([calendar.source.value, calendar.hasOwn.value, calendar.dirty.value]).toEqual(["global", false, false])
		expect(calendar.customersWithCalendar.value).toEqual(["GLOBEX"])
		expect(calendar.draft.value?.week.mon).toEqual([["09:00", "17:00"]])
	})

	it("ignores a load a newer scope superseded", async () => {
		const slow = deferred<unknown>()
		api.getCalendar.mockReturnValueOnce(slow.promise).mockResolvedValueOnce(respond(own))
		const scope = shallowRef<string | null>(null)
		const calendar = withSetup(() => useBusinessCalendar(scope))
		scope.value = "ACME"
		await flushPromises()
		slow.resolve(respond(CALENDAR))
		await flushPromises()
		expect(calendar.source.value).toBe("customer")
		expect(calendar.loading.value).toBe(false)
	})

	it("tracks edits: dirty, a validation error, and discard", async () => {
		api.getCalendar.mockResolvedValueOnce(respond(CALENDAR))
		const calendar = withSetup(() => useBusinessCalendar(shallowRef(null)))
		await flushPromises()
		const draft = calendar.draft.value
		if (!draft) throw new Error("no draft loaded")
		draft.week.mon = [["18:00", "09:00"]]
		await nextTick()
		expect(calendar.dirty.value).toBe(true)
		expect(calendar.error.value).toMatch(/^Monday: a window must start/)
		calendar.discard()
		await nextTick()
		expect([calendar.dirty.value, calendar.error.value]).toEqual([false, null])
	})

	it("saves and removes, reporting each outcome in words", async () => {
		api.getCalendar.mockResolvedValueOnce(respond(CALENDAR))
		const calendar = withSetup(() => useBusinessCalendar(shallowRef("ACME")))
		await flushPromises()

		api.saveCalendar.mockResolvedValueOnce(respond(own, ["ACME"]))
		expect(await calendar.save(true)).toEqual({ ok: true, message: "ok" })
		expect(api.saveCalendar.mock.calls[0][0]).toMatchObject({ customer_code: "ACME", apply_to_open: true, timezone: "Europe/Rome" })
		expect([calendar.hasOwn.value, calendar.customersWithCalendar.value]).toEqual([true, ["ACME"]])

		api.deleteCalendar.mockImplementationOnce(() => Promise.reject(Object.assign(new Error("x"), { response: { data: { detail: "denied" } } })))
		expect(await calendar.remove(false)).toEqual({ ok: false, message: "Could not remove the calendar: denied" })
		expect(calendar.saving.value).toBe(false)
	})

	it("never tries to remove the global calendar", async () => {
		api.getCalendar.mockResolvedValueOnce(respond(CALENDAR))
		const calendar = withSetup(() => useBusinessCalendar(shallowRef(null)))
		await flushPromises()
		expect((await calendar.remove(false)).ok).toBe(false)
		expect(api.deleteCalendar).not.toHaveBeenCalled()
	})

	it("says when the calendar could not be loaded", async () => {
		api.getCalendar.mockImplementationOnce(() => Promise.reject(new Error("offline")))
		const calendar = withSetup(() => useBusinessCalendar(shallowRef(null)))
		await flushPromises()
		expect(calendar.loadError.value).toBe("offline")
	})
})

describe("holidayList", () => {
	function list(initial: string[], readonly = false) {
		const holidays = ref(initial)
		const wrapper = mount(
			defineComponent({
				setup: () => () =>
					h(HolidayList, {
						modelValue: holidays.value,
						"onUpdate:modelValue": (value: string[]) => {
							holidays.value = value
						},
						readonly
					})
			})
		)
		return { wrapper, holidays }
	}

	it("removes a holiday, and shows the empty state", async () => {
		const { wrapper, holidays } = list(["2026-12-25"])
		expect(wrapper.get("[data-testid=calendar-holiday-2026-12-25]").text()).toContain("25 Dec 2026")
		await wrapper.get("[data-testid=calendar-holiday-2026-12-25] .n-tag__close").trigger("click")
		expect(holidays.value).toEqual([])
		await nextTick()
		expect(wrapper.text()).toContain("No holidays")
	})

	it("adds a picked day once, keeping the list sorted", async () => {
		const { wrapper, holidays } = list(["2026-12-25"])
		const picker = wrapper.findComponent({ name: "DatePicker" })
		for (const day of ["2026-01-01", "2026-12-25"]) {
			picker.vm.$emit("update:formatted-value", day)
			await nextTick()
			await wrapper.get("[data-testid=calendar-holiday-add]").trigger("click")
		}
		expect(holidays.value).toEqual(["2026-01-01", "2026-12-25"])
	})

	it("is read-only for analysts", () => {
		const { wrapper } = list(["2026-12-25"], true)
		expect(wrapper.find("[data-testid=calendar-holiday-add]").exists()).toBe(false)
		expect(wrapper.find(".n-tag__close").exists()).toBe(false)
	})
})

describe("small ui", () => {
	it("severityTag names the severity next to its colour", () => {
		const wrapper = mount(SeverityTag, { props: { severity: "Critical" } })
		expect(wrapper.text()).toBe("Critical")
		expect(wrapper.get(".severity-dot").attributes("style")).toContain(SEVERITY_TONE.Critical)
	})

	it("sparkline draws an axis-free ECharts line ending on a marked last value, and nothing for a single point", () => {
		const wrapper = mount(Sparkline, { props: { values: [1, 4, 2] } })
		expect(wrapper.get("[data-testid=v-chart]").attributes("aria-label")).toBe("Trend over 3 periods, peak 4")
		const option = sparkOptions.at(-1) as Record<string, any>
		expect(option.xAxis.show).toBe(false)
		expect(option.yAxis).toMatchObject({ show: false, min: 0, max: 4 })
		const data = option.series[0].data
		expect(data.slice(0, 2)).toEqual([1, 4])
		expect(data[2]).toMatchObject({ value: 2, symbol: "circle" })
		expect(option.tooltip).toEqual({ show: false })
		expect(option.series[0].silent).toBe(true)
		expect(mount(Sparkline, { props: { values: [5] } }).find("[data-testid=v-chart]").exists()).toBe(false)
	})

	it("sparkline with one label per value shows the period and the value on hover", () => {
		mount(Sparkline, { props: { values: [1, 4, 2], labels: ["1 Sep", "2 Sep", "3 Sep"], unit: "alerts" } })
		const option = sparkOptions.at(-1) as Record<string, any>
		expect(option.xAxis.data).toEqual(["1 Sep", "2 Sep", "3 Sep"])
		expect(option.series[0].silent).toBe(false)
		expect(option.tooltip).toMatchObject({ trigger: "axis", appendToBody: true })
		const html = option.tooltip.formatter([{ dataIndex: 1 }]) as string
		expect(html).toContain("2 Sep")
		expect(html).toContain(">4</b> alerts")

		// Labels that do not match the values are ignored rather than misaligned.
		mount(Sparkline, { props: { values: [1, 4, 2], labels: ["1 Sep"] } })
		expect((sparkOptions.at(-1) as Record<string, any>).tooltip).toEqual({ show: false })
	})

	it("socPanel carries its title, caption, actions and body", () => {
		const wrapper = mount(SocPanel, {
			props: { title: "Backlog", caption: "open now" },
			slots: { default: () => h("p", "body"), actions: () => h("button", "act") }
		})
		expect(wrapper.text()).toContain("Backlog")
		expect(wrapper.text()).toContain("open now")
		expect(wrapper.get("button").text()).toBe("act")
		expect(wrapper.text()).toContain("body")
	})

	it("segmentedPanel is a segmented Naive card: header with title, caption and actions, body, footer band", () => {
		const wrapper = mount(SegmentedPanel, {
			props: { title: "Global policy", caption: "cells left at default" },
			slots: {
				default: () => h("p", "matrix"),
				actions: () => h("button", "Follow global"),
				footer: () => h("button", "Save policy")
			}
		})
		const card = wrapper.get(".n-card")
		expect(card.classes()).toEqual(expect.arrayContaining(["soc-segmented-panel", "n-card--content-segmented", "n-card--footer-segmented"]))
		expect(wrapper.get(".n-card-header").text()).toContain("Global policy")
		expect(wrapper.get(".n-card-header").text()).toContain("cells left at default")
		expect(wrapper.get(".n-card-header__extra").text()).toBe("Follow global")
		expect(wrapper.get(".n-card-content").text()).toBe("matrix")
		expect(wrapper.get(".n-card__footer").text()).toBe("Save policy")
		// Header and footer bands share the secondary surface and the page's 12px gutter.
		expect(wrapper.get(".n-card-header").attributes("style")).toContain("background-color: var(--bg-secondary-color)")
		expect(wrapper.get(".n-card__footer").attributes("style")).toContain("padding: 10px 12px")
	})

	it("segmentedPanel leaves out the footer band when there is nothing to commit, and drops body padding when flush", () => {
		const wrapper = mount(SegmentedPanel, { props: { title: "Scope", flush: true }, slots: { default: () => h("nav", "list") } })
		expect(wrapper.find(".n-card__footer").exists()).toBe(false)
		expect(wrapper.find(".n-card-header__extra").exists()).toBe(false)
		expect(wrapper.get(".n-card-content").attributes("style")).toContain("padding: 0")
	})
})
