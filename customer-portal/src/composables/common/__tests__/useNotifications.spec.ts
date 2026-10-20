import type { VNode } from "vue"
import { createPinia, setActivePinia } from "pinia"
import { describe, expect, it, vi } from "vitest"
import { openRoute, useNotifications } from "../useNotifications"

const push = vi.hoisted(() => vi.fn(() => Promise.resolve()))
const destroy = vi.hoisted(() => vi.fn())
const create = vi.hoisted(() => vi.fn((_options: { action: () => VNode }) => ({ destroy })))
vi.mock("@/router", () => ({ default: { push } }))
vi.mock("../useGlobalActions", () => ({ useGlobalActions: () => ({ notification: create }) }))

describe("a notification's target (#1263)", () => {
	it("opens a route with its query, so a notification can say what to do there", () => {
		openRoute({ name: "ReportsList", query: { download: "5" } })
		expect(push).toHaveBeenLastCalledWith({ name: "ReportsList", query: { download: "5" } })
	})

	it("opens a plain route as before, and nothing without one", () => {
		push.mockClear()
		openRoute({ name: "ReportsList" })
		expect(push).toHaveBeenLastCalledWith({ name: "ReportsList", query: undefined })
		openRoute(undefined)
		expect(push).toHaveBeenCalledTimes(1)
	})

	it("survives the bell being saved and read back: the target is plain data", () => {
		const target = { name: "ReportsList", query: { download: "5" } }
		expect(JSON.parse(JSON.stringify(target))).toEqual(target)
	})

	it("closes the toast once its action is used, and goes where it says", () => {
		setActivePinia(createPinia())
		push.mockClear()
		useNotifications().prepend(
			{
				id: "report-5",
				category: "report",
				type: "success",
				title: "Report ready",
				description: "",
				read: false,
				date: new Date(),
				actionRoute: { name: "ReportsList", query: { download: "5" } },
				actionTitle: "Download"
			},
			{ sendNotify: true }
		)
		const options = create.mock.calls.at(-1)![0]
		const button = options.action()
		expect((button.children as { default: () => string }).default()).toBe("Download")
		;(button.props as { onClick: () => void }).onClick()
		expect(destroy).toHaveBeenCalledTimes(1)
		expect(push).toHaveBeenLastCalledWith({ name: "ReportsList", query: { download: "5" } })
	})
})

describe("server notifications in the bell (#1282)", () => {
	it("open an alert or a case by its id", () => {
		openRoute({ name: "AlertDetails", params: { id: "42" } })
		expect(push).toHaveBeenLastCalledWith({ name: "AlertDetails", params: { id: "42" }, query: undefined })
	})

	it("a toast-only item pops the toast and stays out of the session list", () => {
		setActivePinia(createPinia())
		const { list, prepend } = useNotifications()
		list.value = []
		create.mockClear()
		prepend(
			{ id: "report-9", category: "report", type: "success", title: "Report ready", description: "", read: false, date: new Date() },
			{ sendNotify: true, toastOnly: true }
		)
		expect(create).toHaveBeenCalledTimes(1)
		expect(list.value).toEqual([])
	})
})
