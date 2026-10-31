import type { TalonChatMessage } from "@/types/talonChat"
import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import i18n from "@/lang"
import TalonMessage from "../TalonMessage.vue"
import { draft, testRouter } from "./fixtures"

const talonChat = vi.hoisted(() => ({ getDraft: vi.fn() }))
const aiReports = vi.hoisted(() => ({ getAlertAnalysis: vi.fn(), requestAnalysis: vi.fn() }))
vi.mock("@/api", () => ({ default: { talonChat, aiReports } }))

function assistant(overrides: Partial<TalonChatMessage> = {}): TalonChatMessage {
	return {
		id: "run-1-assistant",
		role: "assistant",
		items: [],
		checked: null,
		createdAt: null,
		status: "completed",
		errorCode: null,
		runId: "run-1",
		feedback: null,
		...overrides
	}
}

function render(message: TalonChatMessage, props: Record<string, unknown> = {}) {
	return mount(TalonMessage, { props: { message, ...props }, global: { plugins: [testRouter()] } })
}

beforeEach(() => {
	setActivePinia(createPinia())
	talonChat.getDraft.mockReset().mockResolvedValue({ data: draft() })
	aiReports.getAlertAnalysis.mockReset().mockResolvedValue({
		data: { alert_id: 9, enabled: true, can_request: true, has_analysis: false, investigation: null, report: null, iocs: [] }
	})
})

describe("an Ask Talon message", () => {
	it("renders the model's markup as text: no element, no handler", () => {
		const evil = `<img src=x onerror="window.__xss=1">\n<script>window.__xss=2</script><a href="javascript:alert(1)">x</a>`
		const wrapper = render(assistant({ items: [{ kind: "text", id: "t", text: evil }] }))
		const text = wrapper.get("[data-testid=talon-message-text]")
		expect(text.find("img").exists()).toBe(false)
		expect(text.find("script").exists()).toBe(false)
		expect(text.find("a").exists()).toBe(false)
		expect(text.text()).toContain(`<img src=x onerror="window.__xss=1">`)
		expect(text.html()).toContain("&lt;img")
		expect((window as unknown as { __xss?: number }).__xss).toBeUndefined()
	})

	it("keeps the text's line breaks, and renders no Markdown", () => {
		const wrapper = render(assistant({ items: [{ kind: "text", id: "t", text: "**Bold**\nsecond line" }] }))
		const text = wrapper.get("[data-testid=talon-message-text]")
		expect(text.classes()).toContain("whitespace-pre-wrap")
		expect(text.text()).toBe("**Bold**\nsecond line")
		expect(text.find("strong").exists()).toBe(false)
	})

	it("says what Talon checked, in the user's language", () => {
		i18n.global.locale.value = "de"
		const wrapper = render(assistant({ checked: [{ kind: "alert", count: 1 }, { kind: "event_search", count: 2 }] }))
		expect(wrapper.get("[data-testid=talon-message-checked]").text()).toBe("Geprüft: der Alarm, 2 Ereignissuchen")
	})

	it("says why a turn failed by its code, localized", () => {
		i18n.global.locale.value = "es"
		const wrapper = render(assistant({ status: "failed", errorCode: "busy_user" }))
		expect(wrapper.get("[data-testid=talon-message-error]").text()).toBe(
			"Ya se está escribiendo una respuesta para ti. Espera a que termine."
		)
	})

	it("shows the cards to a user who may change the customer's data", async () => {
		const wrapper = render(
			assistant({ items: [{ kind: "soc-draft", draftId: "d-1" }, { kind: "analysis-offer", alertId: 9 }] }),
			{ showCards: true, canDraft: true, canRequestAnalysis: true }
		)
		await flushPromises()
		expect(wrapper.find("[data-testid=talon-draft-card]").exists()).toBe(true)
		expect(wrapper.find("[data-testid=talon-analysis-offer]").exists()).toBe(true)
		expect(talonChat.getDraft).toHaveBeenCalledWith("d-1", expect.any(AbortSignal))
	})

	it("hides both cards from a read-only user, and loads nothing for them", async () => {
		const wrapper = render(assistant({ items: [{ kind: "soc-draft", draftId: "d-1" }, { kind: "analysis-offer", alertId: 9 }] }), {
			showCards: false
		})
		await flushPromises()
		expect(wrapper.find("[data-testid=talon-draft-card]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=talon-analysis-offer]").exists()).toBe(false)
		expect(talonChat.getDraft).not.toHaveBeenCalled()
		expect(aiReports.getAlertAnalysis).not.toHaveBeenCalled()
	})

	it("offers thumbs up and down on a completed turn, and takes a rating back", async () => {
		const wrapper = render(assistant())
		await wrapper.get("[data-testid=talon-feedback-up]").trigger("click")
		expect(wrapper.emitted("feedback")).toEqual([["up"]])

		const rated = render(assistant({ feedback: "down" }))
		expect(rated.get("[data-testid=talon-feedback-down]").attributes("aria-pressed")).toBe("true")
		await rated.get("[data-testid=talon-feedback-down]").trigger("click")
		expect(rated.emitted("feedback")).toEqual([[null]])
	})

	it("offers no feedback before the turn is read back, nor on a failed one or the user's", () => {
		expect(render(assistant({ runId: null })).find("[data-testid=talon-message-feedback]").exists()).toBe(false)
		expect(render(assistant({ status: "failed", errorCode: "failed" })).find("[data-testid=talon-message-feedback]").exists()).toBe(false)
		expect(render(assistant({ role: "user" })).find("[data-testid=talon-message-feedback]").exists()).toBe(false)
	})
})
