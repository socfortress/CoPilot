import { mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import AlertComment from "../../alerts/AlertComment.vue"
import CaseComment from "../../cases/CaseComment.vue"

vi.mock("@/api", () => ({ default: { incidentManagement: { alerts: {}, cases: {} } } }))

function render(component: unknown, props: Record<string, unknown>) {
	return mount(
		defineComponent({ setup: () => () => h(NMessageProvider, null, () => h(component as never, props as never)) })
	)
}

const base = { id: 1, comment: "Is this ours?", user_name: "jane", created_at: "2026-10-25T21:16:00Z" }

beforeEach(() => {
	setActivePinia(createPinia())
})

/** A comment shows its author's role: on the avatar and beside the name (#1305). */
describe("the role of a comment's author", () => {
	it.each([
		["a case", CaseComment, { ...base, case_id: 4 }],
		["an alert", AlertComment, { ...base, alert_id: 9 }]
	])("is shown on %s's comment", (_, component, comment) => {
		const wrapper = render(component, { comment, authorRole: "customer_user" })
		expect(wrapper.get("[data-testid=comment-author-role]").text()).toBe("Customer User")
		expect(wrapper.get("[data-testid=comment-author-role-badge]").attributes("data-role")).toBe("customer_user")
	})

	it("is left out when it isn't known", () => {
		const wrapper = render(CaseComment, { comment: { ...base, case_id: 4 } })
		expect(wrapper.find("[data-testid=comment-author-role]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=comment-author-role-badge]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=comment-author-avatar]").exists()).toBe(true)
	})
})
