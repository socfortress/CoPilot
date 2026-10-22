import type { VNode } from "vue"
import { mount } from "@vue/test-utils"
import { NDropdown } from "naive-ui"
import { describe, expect, it, vi } from "vitest"
import { defineComponent } from "vue"
import { AuthUserRole } from "@/types/auth"
import Avatar from "../Avatar.vue"

/** The avatar menu opens on who is signed in: the whole username and the role. */

const LONG_NAME = "a.very.long.username.that.would.never.fit@corporate-directory.example"
const store = vi.hoisted(() => ({ userName: "", userRole: 0, userPic: "" }))

vi.mock("@/stores/auth", () => ({ useAuthStore: () => store }))
vi.mock("vue-router", async () => {
	const { defineComponent, h } = await import("vue")
	// A link that names where it goes, as the real one does in its href.
	const RouterLink = defineComponent({
		props: { to: { type: Object, required: true } },
		setup: (props, { slots, attrs }) => () =>
			h("a", { ...attrs, "data-to": (props.to as { name: string }).name }, slots.default?.())
	})
	return { useRouter: () => ({ push: vi.fn() }), RouterLink }
})

function header(role: AuthUserRole) {
	store.userName = LONG_NAME
	store.userRole = role
	const options = mount(Avatar).findComponent(NDropdown).props("options") as { key: string; render?: () => VNode }[]
	const [first] = options
	expect(first.key).toBe("signed-in-user")
	expect(first.render).toBeTypeOf("function")
	return mount(defineComponent({ render: () => first.render?.() }))
}

describe("avatar menu", () => {
	it("shows the whole username, never truncated", () => {
		const name = header(AuthUserRole.Responder).get("[data-testid=avatar-username]")
		expect(name.text()).toBe(LONG_NAME)
		expect(name.classes()).toContain("break-all")
		expect(name.classes()).not.toContain("truncate")
	})

	it("is the way to the Profile, which the menu no longer lists", () => {
		const card = header(AuthUserRole.Analyst).get("[data-testid=avatar-user]")
		expect(card.element.tagName).toBe("A")
		expect(card.attributes("data-to")).toBe("Profile")
		const keys = (mount(Avatar).findComponent(NDropdown).props("options") as { key: string }[]).map(o => o.key)
		expect(keys).not.toContain("route-Profile")
		expect(keys).toContain("route-Logout")
	})

	it("closes the menu when the card is followed", async () => {
		store.userRole = AuthUserRole.Admin
		const wrapper = mount(Avatar)
		const dropdown = wrapper.findComponent(NDropdown)
		dropdown.vm.$emit("update:show", true)
		await wrapper.vm.$nextTick()
		expect(dropdown.props("show")).toBe(true)
		const [first] = dropdown.props("options") as { render: () => VNode }[]
		await mount(defineComponent({ render: () => first.render() })).get("[data-testid=avatar-user]").trigger("click")
		await wrapper.vm.$nextTick()
		expect(dropdown.props("show")).toBe(false)
	})

	it("shows the role by its label", () => {
		expect(header(AuthUserRole.Responder).get("[data-testid=avatar-role]").text()).toBe("Responder")
		expect(header(AuthUserRole.CustomerUser).get("[data-testid=avatar-role]").text()).toBe("Customer User")
	})
})

/** The toolbar shows who is signed in and as what, without opening the menu. */
describe("toolbar account block", () => {
	function block(role: AuthUserRole, name = "someone") {
		store.userName = name
		store.userRole = role
		return mount(Avatar)
	}

	it("shows the username and the role, with a dot in the role's colour", () => {
		const responder = block(AuthUserRole.Responder, "g.conti")
		expect(responder.get("[data-testid=toolbar-avatar-name]").text()).toBe("g.conti")
		expect(responder.get("[data-testid=toolbar-avatar-role]").text()).toBe("Responder")
		expect(responder.get("[data-testid=toolbar-avatar-role] span").attributes("style")).toContain("var(--primary-color)")
		expect(block(AuthUserRole.Analyst).get("[data-testid=toolbar-avatar-role] span").attributes("style")).toContain(
			"var(--info-color)"
		)
	})

	it("cuts a long username on screen but names it whole on hover", () => {
		const wrapper = block(AuthUserRole.Admin, LONG_NAME)
		expect(wrapper.get("[data-testid=toolbar-avatar-name]").classes()).toContain("truncate")
		expect(wrapper.get("[data-testid=toolbar-avatar]").attributes("title")).toBe(`${LONG_NAME} · Admin`)
	})

	it("shows no role while it is unknown", () => {
		expect(block(AuthUserRole.Unknown).find("[data-testid=toolbar-avatar-role]").exists()).toBe(false)
	})
})
