import type { BusinessCalendar, Weekday, WorkingWindow } from "@/types/soc-management"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, ref } from "vue"
import {
	buildCalendarPayload,
	calendarError,
	dayError,
	fromMinutes,
	isCalendarDirty,
	nextWindow,
	timezoneOptions,
	toEditableCalendar,
	toMinutes,
	weeklyMinutes,
	windowSpan
} from "../policies/calendar"
import CalendarPanel from "../policies/CalendarPanel.vue"
import WeekScheduleEditor from "../policies/WeekScheduleEditor.vue"

const getCalendar = vi.fn()
const saveCalendar = vi.fn()
const deleteCalendar = vi.fn()
vi.mock("@/api", () => ({
	default: {
		socManagement: {
			getCalendar: (...args: unknown[]) => getCalendar(...args),
			saveCalendar: (...args: unknown[]) => saveCalendar(...args),
			deleteCalendar: (...args: unknown[]) => deleteCalendar(...args)
		}
	}
}))

const OFFICE: WorkingWindow[] = [["09:00", "17:00"]]

function calendar(over: Partial<BusinessCalendar> = {}): BusinessCalendar {
	return {
		customer_code: null,
		source: "global",
		timezone: "Europe/Rome",
		week: { mon: OFFICE, tue: OFFICE, wed: OFFICE, thu: OFFICE, fri: OFFICE, sat: [], sun: [] },
		holidays: ["2026-12-25"],
		...over
	}
}

beforeEach(() => {
	setActivePinia(createPinia())
	for (const mock of [getCalendar, saveCalendar, deleteCalendar]) mock.mockReset()
})

describe("calendar helpers", () => {
	it("reads and writes HH:MM", () => {
		expect(toMinutes("09:30")).toBe(570)
		expect(toMinutes("24:00")).toBeNull()
		expect(toMinutes("9:30")).toBeNull()
		expect(fromMinutes(570)).toBe("09:30")
		expect(fromMinutes(2000)).toBe("23:59")
	})

	it("validates a day's windows the way the backend does", () => {
		expect(dayError(OFFICE)).toBeNull()
		expect(dayError([["17:00", "09:00"]])).toMatch(/start before it ends/)
		expect(
			dayError([
				["09:00", "13:00"],
				["12:00", "17:00"]
			])
		).toMatch(/overlap/)
		expect(dayError([["9am", "5pm"]])).toMatch(/HH:MM/)
		expect(dayError([])).toBeNull()
	})

	it("refuses a calendar with no working time or no timezone", () => {
		const closed = toEditableCalendar(
			calendar({ week: { mon: [], tue: [], wed: [], thu: [], fri: [], sat: [], sun: [] } })
		)
		expect(calendarError(closed)).toMatch(/at least one day/)
		expect(calendarError({ ...toEditableCalendar(calendar()), timezone: "" })).toMatch(/timezone/)
		const broken = toEditableCalendar(calendar())
		broken.week.tue = [["18:00", "08:00"]]
		expect(calendarError(broken)).toMatch(/^Tuesday: a window must start/)
	})

	it("sums the working week and maps a window onto the day strip", () => {
		expect(weeklyMinutes(toEditableCalendar(calendar()))).toBe(5 * 8 * 60)
		expect(windowSpan(["06:00", "12:00"])).toEqual({ left: 25, width: 25 })
		expect(windowSpan(["12:00", "06:00"])).toBeNull()
	})

	it("adds the next window an hour after the last one", () => {
		expect(nextWindow([])).toEqual(["09:00", "10:00"])
		expect(nextWindow([["09:00", "12:00"]])).toEqual(["12:00", "13:00"])
		expect(nextWindow([["20:00", "23:30"]])).toEqual(["23:30", "23:59"])
	})

	it("builds a payload with closed days left out, windows sorted and holidays de-duplicated", () => {
		const editable = toEditableCalendar(calendar())
		editable.week.mon = [
			["13:00", "17:00"],
			["09:00", "12:00"]
		]
		editable.holidays = ["2026-12-26", "2026-12-25", "2026-12-25"]
		const payload = buildCalendarPayload(editable, "ACME", true)
		expect(payload).toMatchObject({ customer_code: "ACME", timezone: "Europe/Rome", apply_to_open: true })
		expect(payload.week.mon).toEqual([
			["09:00", "12:00"],
			["13:00", "17:00"]
		])
		expect(Object.keys(payload.week)).toEqual(["mon", "tue", "wed", "thu", "fri"])
		expect(payload.holidays).toEqual(["2026-12-25", "2026-12-26"])
	})

	it("is dirty only when what would be saved changes", () => {
		const original = toEditableCalendar(calendar())
		const same = toEditableCalendar(calendar())
		expect(isCalendarDirty(same, original)).toBe(false)
		same.holidays = [...same.holidays, "2026-12-25"] // a duplicate saves the same
		expect(isCalendarDirty(same, original)).toBe(false)
		same.timezone = "UTC"
		expect(isCalendarDirty(same, original)).toBe(true)
	})

	it("offers every zone, keeping one the browser does not know", () => {
		const zones = timezoneOptions("Mars/Olympus").map(option => option.value)
		expect(zones[0]).toBe("Mars/Olympus")
		expect(zones).toContain("UTC")
	})
})

describe("weekScheduleEditor", () => {
	function editor(readonly = false) {
		const week = ref<Record<Weekday, WorkingWindow[]>>(toEditableCalendar(calendar()).week)
		const Host = defineComponent({
			setup: () => () =>
				h(WeekScheduleEditor, {
					modelValue: week.value,
					"onUpdate:modelValue": (value: Record<Weekday, WorkingWindow[]>) => {
						week.value = value
					},
					readonly
				})
		})
		return { wrapper: mount(Host), week }
	}

	it("opens a closed day with office hours and closes an open one", async () => {
		const { wrapper, week } = editor()
		expect(wrapper.get("[data-testid=calendar-day-sat]").text()).toContain("Closed")
		await wrapper.get("[data-testid=calendar-open-sat]").trigger("click")
		expect(week.value.sat).toEqual([["09:00", "17:00"]])
		await wrapper.get("[data-testid=calendar-open-mon]").trigger("click")
		expect(week.value.mon).toEqual([])
	})

	it("adds a window after the last one, and flags an overlap", async () => {
		const { wrapper, week } = editor()
		await wrapper.get("[data-testid=calendar-add-tue]").trigger("click")
		expect(week.value.tue).toEqual([
			["09:00", "17:00"],
			["17:00", "18:00"]
		])
		week.value = { ...week.value, wed: [...OFFICE, ["16:00", "18:00"]] }
		await wrapper.vm.$nextTick()
		expect(wrapper.get("[data-testid=calendar-day-wed]").text()).toContain("Windows overlap")
	})

	it("draws each window as its own block on the strip, labelled when it is wide enough", async () => {
		const { wrapper, week } = editor()
		// A lunch break: two windows that meet, plus a one-hour evening shift.
		week.value = {
			...week.value,
			mon: [
				["08:00", "12:00"],
				["13:00", "19:00"],
				["19:00", "20:00"]
			]
		}
		await wrapper.vm.$nextTick()
		const blocks = wrapper.findAll("[data-testid^=calendar-window-mon-]")
		expect(blocks.map(block => block.attributes("title"))).toEqual(["08:00–12:00", "13:00–19:00", "19:00–20:00"])
		// Full times on a wide window, short ones on a 4-hour one, nothing on a sliver.
		expect(blocks.map(block => block.text())).toEqual(["08–12", "13:00–19:00", ""])
		expect(blocks[0].attributes("style")).toContain("left: 33.3333")
		// A closed day draws no block at all, and every day keeps its hour ticks.
		expect(wrapper.findAll("[data-testid^=calendar-window-sat-]")).toHaveLength(0)
		expect(wrapper.get("[data-testid=calendar-day-sat]").findAll(".tick")).toHaveLength(23)
		expect(wrapper.get("[data-testid=calendar-day-sat]").findAll(".tick.is-major")).toHaveLength(3)
	})

	it("is read-only for analysts", () => {
		const { wrapper } = editor(true)
		expect(wrapper.find("[data-testid=calendar-add-mon]").exists()).toBe(false)
		expect(wrapper.get("[data-testid=calendar-open-mon]").classes().join(" ")).toContain("disabled")
	})
})

describe("calendarPanel", () => {
	function panel(scope: string | null, isAdmin = true) {
		return mount(
			defineComponent({
				setup: () => () =>
					h(NMessageProvider, null, { default: () => h(CalendarPanel, { scope, scopeName: scope, isAdmin }) })
			})
		)
	}

	it("loads the scope's calendar and says where it comes from", async () => {
		getCalendar.mockResolvedValue({
			data: { calendar: calendar({ source: "global" }), customers_with_calendar: ["GLOBEX"], retargeted: 0 }
		})
		const wrapper = panel("ACME")
		await flushPromises()
		expect(getCalendar).toHaveBeenCalledWith("ACME")
		expect(wrapper.get("[data-testid=calendar-source]").text()).toBe("Global calendar")
		expect(wrapper.text()).toContain("ACME follows the global calendar")
		expect(wrapper.get("[data-testid=calendar-weekly-hours]").text()).toContain("40 working hours")
		expect(wrapper.findComponent(CalendarPanel).emitted("changed")?.[0]).toEqual([["GLOBEX"]])
	})

	it("saves the calendar a customer follows as its own, and can drop it again", async () => {
		getCalendar.mockResolvedValue({
			data: { calendar: calendar({ source: "global" }), customers_with_calendar: [], retargeted: 0 }
		})
		const own = {
			calendar: calendar({ source: "customer", customer_code: "ACME" }),
			customers_with_calendar: ["ACME"],
			retargeted: 2
		}
		saveCalendar.mockResolvedValue({ data: { ...own, message: "Saved customer ACME; 2 open item(s) re-targeted" } })
		deleteCalendar.mockResolvedValue({
			data: { calendar: calendar({ source: "global" }), customers_with_calendar: [], retargeted: 0 }
		})
		const wrapper = panel("ACME")
		await flushPromises()

		await wrapper.get("[data-testid=calendar-apply-open]").trigger("click")
		await wrapper.get("[data-testid=calendar-save]").trigger("click")
		await flushPromises()
		expect(saveCalendar).toHaveBeenCalledWith(
			expect.objectContaining({
				customer_code: "ACME",
				timezone: "Europe/Rome",
				holidays: ["2026-12-25"],
				apply_to_open: true
			})
		)
		expect(wrapper.get("[data-testid=calendar-source]").text()).toBe("Customer calendar")
		expect(wrapper.find("[data-testid=calendar-remove]").exists()).toBe(true)
	})

	it("is read-only for analysts", async () => {
		getCalendar.mockResolvedValue({ data: { calendar: calendar(), customers_with_calendar: [], retargeted: 0 } })
		const wrapper = panel(null, false)
		await flushPromises()
		expect(wrapper.find("[data-testid=calendar-save]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=calendar-holiday-add]").exists()).toBe(false)
	})
})
