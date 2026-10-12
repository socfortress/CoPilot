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
vi.mock("vue-router", () => ({ useRouter: () => ({ push: vi.fn() }) }))

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

	it("shows the role by its label", () => {
		expect(header(AuthUserRole.Responder).get("[data-testid=avatar-role]").text()).toBe("Responder")
		expect(header(AuthUserRole.CustomerUser).get("[data-testid=avatar-role]").text()).toBe("Customer User")
	})
})
