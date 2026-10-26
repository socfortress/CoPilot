import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import CommentAuthorAvatar from "../CommentAuthorAvatar.vue"

/** A comment author's avatar with their role on it (#1305). */
describe("the comment author's avatar", () => {
	it("carries the role: a badge with its icon, a ring in its colour, the role in the title", () => {
		const wrapper = mount(CommentAuthorAvatar, { props: { userName: "jane", role: "customer_user" } })
		const badge = wrapper.get("[data-testid=comment-author-role-badge]")
		expect(badge.attributes("data-role")).toBe("customer_user")
		expect(badge.attributes("style")).toContain("var(--success-color)")
		expect(wrapper.get("[data-testid=comment-author-avatar]").attributes("title")).toBe("jane · Customer User")
		expect(wrapper.find(".n-avatar").attributes("style")).toContain("box-shadow")
	})

	it("tells the SOC roles apart", () => {
		const admin = mount(CommentAuthorAvatar, { props: { userName: "boss", role: "admin" } })
		const analyst = mount(CommentAuthorAvatar, { props: { userName: "ana", role: "analyst" } })
		expect(admin.get("[data-testid=comment-author-role-badge]").attributes("style")).toContain("var(--error-color)")
		expect(analyst.get("[data-testid=comment-author-role-badge]").attributes("style")).toContain("var(--info-color)")
	})

	it("is the plain avatar when the role isn't known", () => {
		const wrapper = mount(CommentAuthorAvatar, { props: { userName: "velociraptor-ingest" } })
		expect(wrapper.find("[data-testid=comment-author-role-badge]").exists()).toBe(false)
		expect(wrapper.get("[data-testid=comment-author-avatar]").attributes("title")).toBe("velociraptor-ingest")
	})
})
