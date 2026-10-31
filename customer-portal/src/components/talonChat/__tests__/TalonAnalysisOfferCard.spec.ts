import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import AiAnalysisRequestButton from "@/components/alerts/AlertDetails/AiAnalysisRequestButton.vue"
import TalonAnalysisOfferCard from "../TalonAnalysisOfferCard.vue"
import { testRouter } from "./fixtures"

const aiReports = vi.hoisted(() => ({ getAlertAnalysis: vi.fn(), requestAnalysis: vi.fn() }))
vi.mock("@/api", () => ({ default: { aiReports } }))

function analysis(overrides: Record<string, unknown> = {}) {
	return {
		data: {
			alert_id: 4127,
			enabled: true,
			can_request: true,
			has_analysis: false,
			investigation: null,
			report: null,
			iocs: [],
			...overrides
		}
	}
}

async function render(canRequest = true) {
	const wrapper = mount(TalonAnalysisOfferCard, {
		props: { alertId: 4127, canRequest },
		global: { plugins: [testRouter()] }
	})
	await flushPromises()
	return wrapper
}

beforeEach(() => {
	setActivePinia(createPinia())
	aiReports.getAlertAnalysis.mockReset()
	aiReports.requestAnalysis.mockReset()
})

describe("talon's offer of an AI analysis", () => {
	it("runs the alert's own analysis request, through its gates", async () => {
		aiReports.getAlertAnalysis.mockResolvedValue(analysis())
		aiReports.requestAnalysis.mockResolvedValue({ data: { alert_id: 4127, requested_at: "2026-10-31T10:00:00" } })
		const wrapper = await render()
		expect(aiReports.getAlertAnalysis).toHaveBeenCalledWith(4127, expect.any(AbortSignal))
		expect(wrapper.get("[data-testid=talon-analysis-offer-alert]").attributes("href")).toBe("/alerts/4127")

		wrapper.findComponent(AiAnalysisRequestButton).vm.$emit("request")
		await flushPromises()
		expect(aiReports.requestAnalysis).toHaveBeenCalledWith(4127)
		expect(wrapper.get("[data-testid=talon-analysis-offer-requested]").text()).toContain("The analysis was requested.")
		expect(wrapper.findComponent(AiAnalysisRequestButton).props("inProgress")).toBe(true)
	})

	it("shows the request route's own refusal", async () => {
		aiReports.getAlertAnalysis.mockResolvedValue(analysis())
		aiReports.requestAnalysis.mockRejectedValue({
			response: { status: 429, data: { message: "The daily limit of AI analyses is reached" } }
		})
		const wrapper = await render()
		wrapper.findComponent(AiAnalysisRequestButton).vm.$emit("request")
		await flushPromises()
		expect(wrapper.get("[data-testid=talon-analysis-offer-error]").text()).toBe("The daily limit of AI analyses is reached.")
	})

	it("offers no button when the alert's analysis may not be requested", async () => {
		aiReports.getAlertAnalysis.mockResolvedValue(analysis({ can_request: false }))
		const wrapper = await render()
		expect(wrapper.findComponent(AiAnalysisRequestButton).exists()).toBe(false)
		expect(wrapper.find("[data-testid=talon-analysis-offer-not-allowed]").exists()).toBe(true)
	})

	it("asks nothing when the availability says the user may not request one", async () => {
		const wrapper = await render(false)
		expect(aiReports.getAlertAnalysis).not.toHaveBeenCalled()
		expect(wrapper.findComponent(AiAnalysisRequestButton).exists()).toBe(false)
		expect(wrapper.find("[data-testid=talon-analysis-offer-not-allowed]").exists()).toBe(true)
	})
})
