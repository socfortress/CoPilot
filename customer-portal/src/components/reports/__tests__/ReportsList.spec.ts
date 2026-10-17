import type { IncidentCustomerReport } from "@/types/reports"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"
import { useAuthStore } from "@/stores/auth"
import List from "../List.vue"

const reports = vi.hoisted(() => ({ listReports: vi.fn(), downloadReport: vi.fn() }))
const saveAs = vi.hoisted(() => vi.fn())
vi.mock("@/api", () => ({ default: { reports } }))
vi.mock("file-saver", () => ({ saveAs }))

const LISTED = { id: 5, file_name: "weekly.pdf", report_name: "Weekly", status: "completed" } as IncidentCustomerReport

async function render(url: string) {
	const router = createRouter({
		history: createMemoryHistory(),
		routes: [{ path: "/reports", name: "ReportsList", component: { render: () => null } }]
	})
	await router.push(url)
	const replace = vi.spyOn(router, "replace")
	const wrapper = mount(defineComponent({ setup: () => () => h(NMessageProvider, null, () => h(List)) }), {
		global: { plugins: [router], stubs: { ReportCard: true } }
	})
	await flushPromises()
	return { router, replace, wrapper }
}

describe("reports page: Download from a notification (#1263)", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		vi.clearAllMocks()
		useAuthStore().$patch({ user: { username: "alice", role: "customer_user", customer_codes: ["A"] } as never })
		reports.listReports.mockResolvedValue({ data: { success: true, reports: [LISTED], total_count: 1 } })
		reports.downloadReport.mockResolvedValue({
			data: new Blob(["%PDF-"]),
			headers: { "content-disposition": 'attachment; filename="from-header.pdf"' }
		})
	})

	it("downloads the report ?download= names, then takes it out of the URL", async () => {
		const { router, replace } = await render("/reports?download=9&tab=x")
		expect(reports.downloadReport).toHaveBeenCalledWith(9)
		expect(saveAs.mock.calls[0]![1]).toBe("from-header.pdf")
		expect(replace).toHaveBeenCalledWith({ query: { tab: "x" } })
		expect(router.currentRoute.value.query).toEqual({ tab: "x" })
	})

	it("names the file after the listed report once the list is in", async () => {
		const { router } = await render("/reports")
		await router.push("/reports?download=5")
		await flushPromises()
		expect(saveAs.mock.calls[0]![1]).toBe("weekly.pdf")
	})

	it("falls back to a plain name when neither says one", async () => {
		reports.downloadReport.mockResolvedValue({ data: new Blob(["%PDF-"]), headers: {} })
		await render("/reports?download=9")
		expect(saveAs.mock.calls[0]![1]).toBe("report-9.pdf")
	})

	it("ignores a ?download= that names no report, and still tidies the URL", async () => {
		const { router } = await render("/reports?download=abc")
		expect(reports.downloadReport).not.toHaveBeenCalled()
		expect(router.currentRoute.value.query).toEqual({})
	})

	it("says when the download fails", async () => {
		reports.downloadReport.mockRejectedValue({ response: { data: { detail: "This report is not available." } } })
		await render("/reports?download=9")
		expect(saveAs).not.toHaveBeenCalled()
		expect(document.body.textContent).toContain("This report is not available.")
	})
})
