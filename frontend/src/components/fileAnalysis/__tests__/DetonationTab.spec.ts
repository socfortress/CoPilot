import { flushPromises, mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import DetonationTab from "../tabs/DetonationTab.vue"

/**
 * A detonation whose CAPE report CoPilot couldn't read into a summary (too large, not JSON, …)
 * says why, and still offers the raw report; the raw report is saved exactly as it came,
 * never parsed in the page (#1361).
 */

const getCapeReport = vi.fn()
const saveAs = vi.fn()
const messageError = vi.fn()

vi.mock("@/api", () => ({
	default: { fileAnalysis: { getCapeReport: (...a: unknown[]) => getCapeReport(...a) } }
}))
vi.mock("file-saver", () => ({ saveAs: (...a: unknown[]) => saveAs(...a) }))
vi.mock("naive-ui", async original => ({
	...(await original<typeof import("naive-ui")>()),
	useMessage: () => ({ success: vi.fn(), error: messageError, warning: vi.fn() })
}))

const REASON = "The CAPE report is larger than CoPilot reads (256 MB, CAPE_REPORT_MAX_MB)."

beforeEach(() => {
	getCapeReport.mockReset()
	saveAs.mockReset()
	messageError.mockReset()
})

describe("file analysis Detonation tab", () => {
	it("says why a report gave no summary and offers the raw report", () => {
		const wrapper = mount(DetonationTab, {
			props: { sandbox: null, dynamicStatus: "failed", dynamicError: REASON, jobId: "job-1361" }
		})

		const failure = wrapper.get("[data-testid='detonation-report-error']")
		expect(failure.text()).toContain("The sandbox ran, but CoPilot couldn't use its report.")
		expect(failure.text()).toContain(REASON)
		expect(failure.text()).not.toContain("platform mismatch")
		expect(failure.get("button").text()).toBe("Download the raw CAPE report")
	})

	it("keeps the platform-mismatch explanation when there is no reason", () => {
		const wrapper = mount(DetonationTab, { props: { sandbox: null, dynamicStatus: "failed", jobId: "job-1361" } })

		expect(wrapper.find("[data-testid='detonation-report-error']").exists()).toBe(false)
		expect(wrapper.text()).toContain("platform mismatch")
	})

	it("saves the raw report exactly as it came", async () => {
		const report = new Blob(['{"info":{"id":42}}'], { type: "application/json" })
		getCapeReport.mockResolvedValue({ data: report })
		const wrapper = mount(DetonationTab, {
			props: { sandbox: null, dynamicStatus: "failed", dynamicError: REASON, jobId: "job-1361" }
		})

		await wrapper.get("[data-testid='detonation-report-error'] button").trigger("click")
		await flushPromises()

		expect(getCapeReport).toHaveBeenCalledWith("job-1361")
		expect(saveAs).toHaveBeenCalledTimes(1)
		expect(saveAs.mock.calls[0][0]).toBe(report)
		expect(saveAs.mock.calls[0][1]).toBe("cape-report-job-1361.json")
	})

	it("says so when the raw report can't be fetched", async () => {
		getCapeReport.mockRejectedValue(new Error("502"))
		const wrapper = mount(DetonationTab, {
			props: { sandbox: null, dynamicStatus: "failed", dynamicError: REASON, jobId: "job-1361" }
		})

		await wrapper.get("[data-testid='detonation-report-error'] button").trigger("click")
		await flushPromises()

		expect(saveAs).not.toHaveBeenCalled()
		expect(messageError).toHaveBeenCalledWith("Could not fetch the full CAPE report.")
	})
})
