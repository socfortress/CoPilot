import { flushPromises, mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import PortalChatReview from "../PortalChatReview.vue"

const listThreads = vi.fn()
const getMessages = vi.fn()

vi.mock("@/api", () => ({
	default: {
		talonPortalReview: {
			listThreads: (...args: unknown[]) => listThreads(...args),
			getMessages: (...args: unknown[]) => getMessages(...args)
		}
	}
}))
vi.mock("@/stores/settings", () => ({ useSettingsStore: () => ({ dateFormat: { datetime: "YYYY-MM-DD HH:mm" } }) }))

const THREAD = {
	id: "0b6f0c55-7a39-4e57-9d6e-3f1a2b3c4d5e",
	title: "<b>HOST-A</b>",
	customer_code: "ACME",
	user_id: "10",
	status: "active",
	turns: 1,
	feedback: { up: 1, down: 0 }
}

beforeEach(() => {
	listThreads.mockReset()
	getMessages.mockReset()
})

describe("the portal chat review", () => {
	it("lists the customer's threads and shows a transcript as text only", async () => {
		listThreads.mockResolvedValue({ data: { threads: [THREAD], next: null } })
		getMessages.mockResolvedValue({
			data: {
				thread: THREAD,
				messages: [
					{ id: "r1-user", role: "user", parts: [{ type: "text", text: "<img src=x onerror=alert(1)>" }] },
					{
						id: "r1-assistant",
						role: "assistant",
						parts: [
							{ type: "data-checked", data: { items: [{ kind: "alert", count: 1 }] } },
							{ type: "text", text: "Nothing to worry about." }
						],
						metadata: { status: "completed", feedback: "up" }
					}
				],
				next: null
			}
		})
		const wrapper = mount(PortalChatReview, { props: { customerCode: "ACME" } })
		await flushPromises()
		expect(listThreads).toHaveBeenCalledWith("ACME", { status: "all", cursor: null })
		const thread = wrapper.get("[data-testid=portal-chat-review-thread]")
		expect(thread.text()).toContain("<b>HOST-A</b>")
		expect(thread.find("b").exists()).toBe(false)

		await thread.trigger("click")
		await flushPromises()
		expect(getMessages).toHaveBeenCalledWith(THREAD.id, { before: null })
		const turns = wrapper.findAll("[data-testid=portal-chat-review-turn]")
		expect(turns.map(t => t.attributes("data-who"))).toEqual(["customer", "talon"])
		expect(turns[0]?.text()).toContain("<img src=x onerror=alert(1)>")
		expect(wrapper.find("img").exists()).toBe(false)
		expect(turns[1]?.text()).toContain("Checked: the alert")
		expect(turns[1]?.get("[data-testid=portal-chat-review-feedback]").text()).toContain("helpful")
	})

	it("explains a refused review by its code", async () => {
		listThreads.mockRejectedValue({
			response: {
				status: 403,
				data: { detail: "you can't review this customer's portal chats", code: "review_forbidden" }
			}
		})
		const wrapper = mount(PortalChatReview, { props: { customerCode: "ACME" } })
		await flushPromises()
		expect(wrapper.get("[data-testid=portal-chat-review-refused]").text()).toContain(
			"an analyst or responder with this customer and access to all of its alert tags"
		)
	})
})
