import type { AiAlertAnalysis, AiInvestigation } from "@/types/aiReports"
import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import AiAnalysisRequestButton from "../AiAnalysisRequestButton.vue"
import AlertAiReport from "../AlertAiReport.vue"

const getAlertAnalysis = vi.hoisted(() => vi.fn())
const requestAnalysis = vi.hoisted(() => vi.fn())
vi.mock("@/api", () => ({ default: { aiReports: { getAlertAnalysis, requestAnalysis } } }))

const NOW = Date.parse("2026-10-09T12:00:00Z")

/** The backend's format: UTC, no offset. */
function minutesAgo(minutes: number) {
	return new Date(NOW - minutes * 60_000).toISOString().replace("Z", "").replace(/\.\d+$/, "")
}

function job(status: string, startedMinutesAgo = 5): AiInvestigation {
	const at = minutesAgo(startedMinutesAgo)
	return { status, triggered_by: "manual", created_at: at, started_at: at, completed_at: status === "completed" ? at : null }
}

function analysis(over: Partial<AiAlertAnalysis> = {}) {
	return {
		data: {
			alert_id: 7,
			enabled: true,
			can_request: true,
			has_analysis: false,
			investigation: null,
			report: null,
			iocs: [],
			success: true,
			message: "",
			...over
		}
	}
}

function done(over: Partial<AiAlertAnalysis> = {}) {
	return analysis({ has_analysis: true, investigation: job("completed", 120), ...over })
}

async function render() {
	const wrapper = mount(AlertAiReport, { props: { alertId: 7 } })
	await flushPromises()
	return wrapper
}

function button(wrapper: Awaited<ReturnType<typeof render>>) {
	return wrapper.findComponent(AiAnalysisRequestButton)
}

beforeEach(() => {
	setActivePinia(createPinia())
	vi.useFakeTimers({ toFake: ["setInterval", "clearInterval", "Date"] })
	vi.setSystemTime(NOW)
	getAlertAnalysis.mockReset()
	requestAnalysis.mockReset()
})

afterEach(() => {
	vi.useRealTimers()
})

describe("asking for an AI analysis from the AI Report tab (#1215)", () => {
	it("is not offered where the customer does not allow it", async () => {
		getAlertAnalysis.mockResolvedValue(analysis({ can_request: false }))
		const wrapper = await render()
		expect(button(wrapper).exists()).toBe(false)
	})

	it("offers a first analysis on an alert that has none", async () => {
		getAlertAnalysis.mockResolvedValue(analysis())
		const wrapper = await render()
		expect(button(wrapper).props()).toMatchObject({ hasAnalysis: false, inProgress: false })
		expect(wrapper.get("[data-testid=ai-request-button]").text()).toBe("Run AI analysis")
	})

	it("offers to re-run a finished analysis", async () => {
		getAlertAnalysis.mockResolvedValue(done())
		const wrapper = await render()
		expect(wrapper.get("[data-testid=ai-request-button]").text()).toBe("Re-run AI analysis")
	})

	it("waits for the requested analysis and refreshes until it has finished", async () => {
		getAlertAnalysis.mockResolvedValue(done())
		requestAnalysis.mockResolvedValue({ data: { alert_id: 7, requested_at: minutesAgo(0), success: true, message: "" } })
		const wrapper = await render()

		await button(wrapper).vm.$emit("request")
		await flushPromises()
		expect(requestAnalysis).toHaveBeenCalledWith(7)
		// The previous analysis is still the latest one: the tab knows a new one is coming.
		expect(wrapper.find("[data-testid=ai-request-pending]").exists()).toBe(true)
		expect(wrapper.get("[data-testid=ai-request-button]").text()).toBe("Analysis in progress")
		expect(wrapper.get("[data-testid=ai-request-button]").attributes("disabled")).toBeDefined()

		// Talon starts it: the new job shows up as running.
		getAlertAnalysis.mockResolvedValue(analysis({ has_analysis: true, investigation: job("running", 0) }))
		await vi.advanceTimersByTimeAsync(15_000)
		await flushPromises()
		expect(wrapper.find("[data-testid=ai-request-pending]").exists()).toBe(false)
		expect(wrapper.get("[data-testid=ai-request-button]").text()).toBe("Analysis in progress")

		// It finishes: the tab stops refreshing.
		getAlertAnalysis.mockResolvedValue(done({ investigation: job("completed", 0) }))
		await vi.advanceTimersByTimeAsync(15_000)
		await flushPromises()
		expect(wrapper.get("[data-testid=ai-request-button]").text()).toBe("Re-run AI analysis")
		const calls = getAlertAnalysis.mock.calls.length
		await vi.advanceTimersByTimeAsync(60_000)
		expect(getAlertAnalysis.mock.calls.length).toBe(calls)
	})

	it("shows why a request was refused, and lets the user try again", async () => {
		getAlertAnalysis.mockResolvedValue(analysis())
		requestAnalysis.mockRejectedValue({
			response: {
				status: 429,
				data: { success: false, message: "Your organization has reached its daily limit of AI analyses. Please try again later." }
			}
		})
		const wrapper = await render()
		await button(wrapper).vm.$emit("request")
		await flushPromises()
		expect(wrapper.get("[data-testid=ai-request-error]").text()).toContain("daily limit")
		expect(button(wrapper).props("inProgress")).toBe(false)
	})

	it("treats an analysis already running as in progress, unless it has been stuck for hours", async () => {
		getAlertAnalysis.mockResolvedValue(analysis({ has_analysis: true, investigation: job("running", 20) }))
		let wrapper = await render()
		expect(button(wrapper).props("inProgress")).toBe(true)

		getAlertAnalysis.mockResolvedValue(analysis({ has_analysis: true, investigation: job("running", 3 * 60) }))
		wrapper = await render()
		expect(button(wrapper).props("inProgress")).toBe(false)
	})
})

describe("aiAnalysisRequestButton", () => {
	it("asks for confirmation before requesting", async () => {
		const wrapper = mount(AiAnalysisRequestButton, {
			props: { hasAnalysis: false, inProgress: false, requesting: false },
			attachTo: document.body
		})
		await wrapper.get("[data-testid=ai-request-button]").trigger("click")
		await flushPromises()
		expect(document.body.querySelector("[data-testid=ai-request-confirm]")?.textContent).toContain("analyse this alert?")
		expect(wrapper.emitted("request")).toBeUndefined()

		const confirm = [...document.body.querySelectorAll("button")].find(b => b.textContent?.includes("Run analysis"))
		confirm?.click()
		await flushPromises()
		expect(wrapper.emitted("request")).toHaveLength(1)
		wrapper.unmount()
	})
})
