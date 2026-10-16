import type { IncidentCustomerReport } from "@/types/reports"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import ReportCard from "../ReportCard.vue"

function report(extra: Partial<IncidentCustomerReport> = {}): IncidentCustomerReport {
	return {
		id: 5,
		report_name: "Weekly",
		customer_code: "A",
		file_name: "weekly.pdf",
		file_size: 2048,
		generated_at: "2026-10-16T09:57:00",
		generated_by: 1,
		generated_by_role: "customer_user",
		date_from: "2026-10-01T00:00:00",
		date_to: "2026-10-16T00:00:00",
		filters_applied: {},
		total_alerts: 0,
		total_cases: 0,
		open_cases: 0,
		closed_cases: 0,
		status: "processing",
		...extra
	}
}

const statusText = (wrapper: ReturnType<typeof mount>) => wrapper.find("[data-testid=report-status]").text()

describe("reportCard (#1263)", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		vi.useFakeTimers()
		vi.setSystemTime(new Date("2026-10-16T10:00:00Z"))
	})
	afterEach(() => vi.useRealTimers())

	it("says for how long a report has been generating, and keeps counting", async () => {
		const wrapper = mount(ReportCard, { props: { report: report() } })
		expect(statusText(wrapper)).toBe("Generating · 3 min")
		await vi.advanceTimersByTimeAsync(2 * 60_000)
		expect(statusText(wrapper)).toBe("Generating · 5 min")
		expect(wrapper.find("button").exists() && wrapper.text()).not.toContain("Download")
	})

	it("shows a finished report's status alone, and its download only when completed", () => {
		const completed = mount(ReportCard, { props: { report: report({ status: "completed" }) } })
		expect(statusText(completed)).toBe("Completed")
		expect(completed.text()).toContain("Download")
		const failed = mount(ReportCard, {
			props: { report: report({ status: "failed", error_message: "The report could not be generated." }) }
		})
		expect(statusText(failed)).toBe("Failed")
		expect(failed.text()).toContain("The report could not be generated.")
		expect(failed.text()).not.toContain("Download")
	})
})
