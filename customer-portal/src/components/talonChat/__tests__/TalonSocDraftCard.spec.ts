import type { VueWrapper } from "@vue/test-utils"
import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import i18n from "@/lang"
import { DRAFT_EDITS } from "../talonChat"
import TalonSocDraftCard from "../TalonSocDraftCard.vue"
import { draft } from "./fixtures"

const talonChat = vi.hoisted(() => ({ getDraft: vi.fn(), submitDraft: vi.fn(), discardDraft: vi.fn() }))
vi.mock("@/api", () => ({ default: { talonChat } }))

function refusal(status: number, code: string) {
	return { response: { status, data: { detail: "the English fallback", code } } }
}

async function render(canDraft = true) {
	const wrapper = mount(TalonSocDraftCard, { props: { draftId: "d-1", canDraft } })
	await flushPromises()
	return wrapper
}

async function choose(wrapper: VueWrapper, group: string, value: string) {
	const input = wrapper.findAll(`[data-testid=${group}] input`).find(i => i.element.getAttribute("value") === value)
	await input?.setValue(true)
}

async function submit(wrapper: VueWrapper) {
	await wrapper.get("[data-testid=talon-draft-form]").trigger("submit")
	await flushPromises()
}

beforeEach(() => {
	setActivePinia(createPinia())
	for (const fn of Object.values(talonChat)) fn.mockReset()
})

describe("a SOC draft card", () => {
	it("reads the draft by its id and lets the user edit Talon's question", async () => {
		talonChat.getDraft.mockResolvedValue({ data: draft() })
		const wrapper = await render()
		expect(talonChat.getDraft).toHaveBeenCalledWith("d-1", expect.any(AbortSignal))
		expect(wrapper.get("[data-testid=talon-draft-target]").text()).toBe("About alert #4127")
		const textarea = wrapper.get("[data-testid=talon-draft-question] textarea").element as HTMLTextAreaElement
		expect(textarea.value).toBe("Was the scheduled task on HOST-A expected?")
	})

	it("sends nothing until the user picks the urgency: Talon never picks it", async () => {
		talonChat.getDraft.mockResolvedValue({ data: draft() })
		const wrapper = await render()
		const checked = wrapper.findAll("[data-testid=talon-draft-urgency] input").filter(i => (i.element as HTMLInputElement).checked)
		expect(checked).toHaveLength(0)
		await submit(wrapper)
		expect(talonChat.submitDraft).not.toHaveBeenCalled()
		expect(wrapper.get("[data-testid=talon-draft-urgency-problem]").text()).toBe("Choose how urgent it is")
	})

	it("files an alert draft on its case by default, with the edited question, and shows the result", async () => {
		talonChat.getDraft.mockResolvedValue({ data: draft() })
		talonChat.submitDraft.mockResolvedValue({ data: { request_id: 812 } })
		const wrapper = await render()
		await wrapper.get("[data-testid=talon-draft-question] textarea").setValue("  Was it expected?\r\nThanks  ")
		await choose(wrapper, "talon-draft-urgency", "high")
		await submit(wrapper)
		expect(talonChat.submitDraft).toHaveBeenCalledWith("d-1", {
			question: "Was it expected?\nThanks",
			urgency: "high",
			file_on: "case"
		})
		expect(wrapper.get("[data-testid=talon-draft-status]").text()).toBe("Sent to the SOC")
		expect(wrapper.get("[data-testid=talon-draft-submitted]").text()).toContain("request #812")
		expect(wrapper.find("[data-testid=talon-draft-form]").exists()).toBe(false)
	})

	it("files on the alert itself when the user says so", async () => {
		talonChat.getDraft.mockResolvedValue({ data: draft() })
		talonChat.submitDraft.mockResolvedValue({ data: { request_id: 813 } })
		const wrapper = await render()
		await choose(wrapper, "talon-draft-urgency", "low")
		await choose(wrapper, "talon-draft-file-on", "alert")
		await submit(wrapper)
		expect(talonChat.submitDraft).toHaveBeenCalledWith("d-1", expect.objectContaining({ file_on: "alert", urgency: "low" }))
	})

	it("asks no file_on for a case draft", async () => {
		talonChat.getDraft.mockResolvedValue({ data: draft({ target: { kind: "case", id: 55 } }) })
		talonChat.submitDraft.mockResolvedValue({ data: { request_id: 1 } })
		const wrapper = await render()
		expect(wrapper.find("[data-testid=talon-draft-file-on]").exists()).toBe(false)
		await choose(wrapper, "talon-draft-urgency", "normal")
		await submit(wrapper)
		expect(talonChat.submitDraft).toHaveBeenCalledWith("d-1", { question: draft().question, urgency: "normal" })
	})

	it("keeps the question within the Ask the SOC form's limits", async () => {
		talonChat.getDraft.mockResolvedValue({ data: draft() })
		const wrapper = await render()
		await wrapper.get("[data-testid=talon-draft-question] textarea").setValue("a".repeat(2001))
		await choose(wrapper, "talon-draft-urgency", "high")
		await submit(wrapper)
		expect(talonChat.submitDraft).not.toHaveBeenCalled()
		expect(wrapper.get("[data-testid=talon-draft-problem]").text()).toBe("Keep the question under 2000 characters")
		await wrapper.get("[data-testid=talon-draft-question] textarea").setValue("ok‮evil")
		await submit(wrapper)
		expect(talonChat.submitDraft).not.toHaveBeenCalled()
	})

	it("says why CoPilot refused, by code and in the user's language, and keeps the form", async () => {
		talonChat.getDraft.mockResolvedValue({ data: draft() })
		talonChat.submitDraft.mockRejectedValue(refusal(429, "soc_request_cooldown"))
		i18n.global.locale.value = "it"
		const wrapper = await render()
		await choose(wrapper, "talon-draft-urgency", "high")
		await submit(wrapper)
		expect(wrapper.get("[data-testid=talon-draft-error]").text()).toBe(
			"È appena stata inviata una domanda su questo. Riprova tra qualche minuto."
		)
		expect(wrapper.find("[data-testid=talon-draft-form]").exists()).toBe(true)
	})

	it("shows an expired draft as expired, and one decided elsewhere as it now is", async () => {
		talonChat.getDraft.mockResolvedValue({ data: draft() })
		talonChat.submitDraft.mockRejectedValue(refusal(409, "draft_expired"))
		const expired = await render()
		await choose(expired, "talon-draft-urgency", "high")
		await submit(expired)
		expect(expired.get("[data-testid=talon-draft-status]").text()).toBe("This draft expired")

		talonChat.submitDraft.mockRejectedValue(refusal(409, "draft_conflict"))
		const conflict = await render()
		talonChat.getDraft.mockResolvedValue({ data: draft({ status: "submitted", copilot_ref: "77" }) })
		await choose(conflict, "talon-draft-urgency", "high")
		await submit(conflict)
		expect(conflict.get("[data-testid=talon-draft-status]").text()).toBe("Sent to the SOC")
		expect(conflict.get("[data-testid=talon-draft-submitted]").text()).toContain("request #77")
	})

	it("discards a draft", async () => {
		talonChat.getDraft.mockResolvedValue({ data: draft() })
		talonChat.discardDraft.mockResolvedValue({ data: draft({ status: "discarded" }) })
		const wrapper = await render()
		await wrapper.get("[data-testid=talon-draft-discard]").trigger("click")
		await flushPromises()
		expect(talonChat.discardDraft).toHaveBeenCalledWith("d-1")
		expect(wrapper.get("[data-testid=talon-draft-status]").text()).toBe("Discarded")
	})

	it("offers no form when the customer takes no questions to the SOC", async () => {
		talonChat.getDraft.mockResolvedValue({ data: draft() })
		const wrapper = await render(false)
		expect(wrapper.find("[data-testid=talon-draft-form]").exists()).toBe(false)
		expect(wrapper.get("[data-testid=talon-draft-off]").text()).toBe("Questions to the SOC are turned off for your organization.")
	})

	it("says when the draft is gone", async () => {
		talonChat.getDraft.mockRejectedValue(refusal(404, "draft_not_found"))
		const wrapper = await render()
		expect(wrapper.get("[data-testid=talon-draft-load-error]").text()).toContain("This draft is no longer available.")
	})

	it("renders Talon's question as text in every state", async () => {
		talonChat.getDraft.mockResolvedValue({ data: draft({ status: "submitted", question: "<img src=x onerror=alert(1)>" }) })
		const wrapper = await render()
		expect(wrapper.find("img").exists()).toBe(false)
		expect(wrapper.get("[data-testid=talon-draft-question-text]").text()).toBe("<img src=x onerror=alert(1)>")
	})

	it("offers the form again for a draft whose send never finished (10 minutes after its claim)", async () => {
		const longAgo = new Date(Date.now() - 11 * 60_000).toISOString()
		talonChat.getDraft.mockResolvedValue({ data: draft({ status: "submitting", claimed_at: longAgo }) })
		const stale = await render()
		expect(stale.find("[data-testid=talon-draft-form]").exists()).toBe(true)
		// Only a pending draft may be discarded.
		expect(stale.find("[data-testid=talon-draft-discard]").exists()).toBe(false)

		const recent = new Date(Date.now() - 2 * 60_000).toISOString()
		talonChat.getDraft.mockResolvedValue({ data: draft({ status: "submitting", claimed_at: recent }) })
		const fresh = await render()
		expect(fresh.find("[data-testid=talon-draft-form]").exists()).toBe(false)
		expect(fresh.get("[data-testid=talon-draft-status]").text()).toBe("Being sent to the SOC…")
	})

	it("reads the draft again after a failure without a code: it may have been filed", async () => {
		talonChat.getDraft.mockResolvedValue({ data: draft() })
		talonChat.submitDraft.mockRejectedValue({ response: { status: 502, data: "Bad gateway" } })
		const wrapper = await render()
		await choose(wrapper, "talon-draft-urgency", "high")
		talonChat.getDraft.mockResolvedValue({ data: draft({ status: "submitted", copilot_ref: "90" }) })
		await submit(wrapper)
		expect(talonChat.getDraft).toHaveBeenCalledTimes(2)
		expect(wrapper.get("[data-testid=talon-draft-status]").text()).toBe("Sent to the SOC")
	})

	it("keeps what the user typed when the card is mounted again in the same conversation", async () => {
		talonChat.getDraft.mockResolvedValue({ data: draft() })
		const edits = new Map()
		const first = mount(TalonSocDraftCard, { props: { draftId: "d-1", canDraft: true }, global: { provide: { [DRAFT_EDITS as symbol]: edits } } })
		await flushPromises()
		await first.get("[data-testid=talon-draft-question] textarea").setValue("My own words")
		await choose(first, "talon-draft-urgency", "low")
		await choose(first, "talon-draft-file-on", "alert")
		first.unmount()

		const again = mount(TalonSocDraftCard, { props: { draftId: "d-1", canDraft: true }, global: { provide: { [DRAFT_EDITS as symbol]: edits } } })
		await flushPromises()
		expect((again.get("[data-testid=talon-draft-question] textarea").element as HTMLTextAreaElement).value).toBe("My own words")
		const checked = again.findAll("input").filter(i => (i.element as HTMLInputElement).checked).map(i => i.attributes("value"))
		expect(checked.sort()).toEqual(["alert", "low"])
	})
})
