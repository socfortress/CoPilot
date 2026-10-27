import type { VNode } from "vue"
import { mount } from "@vue/test-utils"
import { NDropdown } from "naive-ui"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent } from "vue"
import Avatar from "../Avatar.vue"

const store = vi.hoisted(() => ({
	isCustomerAdmin: false,
	userPic: "",
	userName: "giulia.bianchi",
	accessibleCustomers: [{ customer_code: "ACME", customer_name: "Acme" }] as {
		customer_code: string
		customer_name: string
		read_only?: boolean
	}[],
	get writableCustomers() {
		return this.accessibleCustomers.filter(customer => !customer.read_only)
	}
}))
const push = vi.hoisted(() => vi.fn())
vi.mock("@/stores/auth", () => ({ useAuthStore: () => store }))
const audit = vi.hoisted(() => ({ available: { value: false }, check: vi.fn() }))
vi.mock("@/composables/common/useAuditAvailability", async () => {
	const { ref } = await import("vue")
	const available = ref(false)
	Object.defineProperty(audit, "available", { value: available })
	return { useAuditAvailability: () => ({ available, check: audit.check }) }
})
// The portal's language (#1310): a store the tests set, and naive's messages recorded.
const locales = vi.hoisted(() => ({ value: null as null | Record<string, unknown> }))
vi.mock("@/stores/i18n", async () => {
	const { reactive } = await import("vue")
	const state = reactive({
		locale: "en",
		available: ["en"],
		get canChoose() {
			return state.available.length > 1
		},
		choose: vi.fn()
	})
	locales.value = state
	return { useLocalesStore: () => state }
})
const message = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn() }))
vi.mock("naive-ui", async importOriginal => ({ ...(await importOriginal<object>()), useMessage: () => message }))
vi.mock("vue-router", async () => {
	const { defineComponent, h } = await import("vue")
	// A link that names where it goes, as the real one does in its href.
	const RouterLink = defineComponent({
		props: { to: { type: Object, required: true } },
		setup: (props, { slots, attrs }) => () =>
			h("a", { ...attrs, "data-to": (props.to as { name: string }).name }, slots.default?.())
	})
	return { useRouter: () => ({ push }), RouterLink }
})

function options() {
	return mount(Avatar).getComponent(NDropdown).props("options") as { key: string; render?: () => VNode }[]
}

function keys() {
	return options().map(option => option.key)
}

function userCard() {
	const [first] = options()
	expect(first?.key).toBe("signed-in-user")
	return mount(defineComponent({ render: () => first?.render?.() }))
}

/** The toolbar says who is signed in and as what; a customer admin's menu offers Users (#1296). */
describe("avatar", () => {
	beforeEach(() => {
		push.mockReset()
		audit.check.mockReset()
		audit.available.value = false
		Object.assign(locales.value ?? {}, { locale: "en", available: ["en"] })
		;(locales.value?.choose as ReturnType<typeof vi.fn>)?.mockReset()
		message.success.mockReset()
		message.error.mockReset()
	})

	it("shows a portal user's name and role, tagged Portal user, with no Users", () => {
		store.isCustomerAdmin = false
		const wrapper = mount(Avatar)
		expect(wrapper.get("[data-testid=toolbar-avatar-name]").text()).toBe("giulia.bianchi")
		expect(wrapper.get("[data-testid=toolbar-avatar-role]").text()).toBe("Portal user")
		expect(wrapper.get("[data-testid=toolbar-avatar]").attributes("title")).toBe("giulia.bianchi · Portal user")
		expect(keys()).toEqual(["signed-in-user", "route-Logout"])
		expect(userCard().get("[data-testid=toolbar-role]").text()).toBe("Portal user")
	})

	it("shows a user who may only read every customer as a read-only user (#1312)", () => {
		store.isCustomerAdmin = false
		store.accessibleCustomers = [{ customer_code: "ACME", customer_name: "Acme", read_only: true }]
		const wrapper = mount(Avatar)
		expect(wrapper.get("[data-testid=toolbar-avatar-role]").text()).toBe("Read-only user")
		store.accessibleCustomers = [{ customer_code: "ACME", customer_name: "Acme" }]
	})

	it("shows a customer admin as such, in the toolbar and on the menu's user card", () => {
		store.isCustomerAdmin = true
		const wrapper = mount(Avatar)
		expect(wrapper.get("[data-testid=toolbar-avatar-role]").text()).toBe("Customer admin")
		expect(wrapper.get("[data-testid=toolbar-avatar-role] span").attributes("style")).toContain("var(--info-color)")
		expect(userCard().get("[data-testid=toolbar-role]").text()).toBe("Customer admin")
	})

	it("offers Users to a customer admin, above Logout", () => {
		store.isCustomerAdmin = true
		expect(keys()).toEqual(["signed-in-user", "route-Users", "route-Logout"])
	})

	it("makes the user card the way to the Profile, closing the menu", async () => {
		store.isCustomerAdmin = false
		const wrapper = mount(Avatar)
		const dropdown = wrapper.getComponent(NDropdown)
		dropdown.vm.$emit("update:show", true)
		await wrapper.vm.$nextTick()
		const card = userCard().get("[data-testid=toolbar-user]")
		expect(card.element.tagName).toBe("A")
		expect(card.attributes("data-to")).toBe("Profile")
		const [first] = dropdown.props("options") as { render: () => VNode }[]
		await mount(defineComponent({ render: () => first?.render() })).get("[data-testid=toolbar-user]").trigger("click")
		await wrapper.vm.$nextTick()
		expect(dropdown.props("show")).toBe(false)
	})

	it("opens the page a key names", () => {
		store.isCustomerAdmin = true
		mount(Avatar).getComponent(NDropdown).vm.$emit("select", "route-Users")
		expect(push).toHaveBeenCalledWith({ name: "Users" })
	})

	it("offers the Audit log to a customer admin once their SOC turned it on (#1298)", () => {
		store.isCustomerAdmin = true
		expect(keys()).toEqual(["signed-in-user", "route-Users", "route-Logout"])
		expect(audit.check).toHaveBeenCalled()
		audit.available.value = true
		expect(keys()).toEqual(["signed-in-user", "route-Users", "route-AuditLog", "route-Logout"])
		mount(Avatar).getComponent(NDropdown).vm.$emit("select", "route-AuditLog")
		expect(push).toHaveBeenCalledWith({ name: "AuditLog" })
	})

	it("never asks, nor offers it, for a plain portal user", () => {
		store.isCustomerAdmin = false
		audit.available.value = true
		expect(keys()).toEqual(["signed-in-user", "route-Logout"])
		expect(audit.check).not.toHaveBeenCalled()
	})

	it("offers no language menu while the customers offer English only (#1310)", () => {
		store.isCustomerAdmin = false
		expect(keys()).toEqual(["signed-in-user", "route-Logout"])
	})

	it("offers the customers' languages, each in its own name, the current one ticked", () => {
		store.isCustomerAdmin = false
		Object.assign(locales.value ?? {}, { locale: "it", available: ["en", "it", "nl"] })
		const language = options().find(option => option.key === "language") as unknown as {
			label: string
			children: { key: string; label: string; icon?: unknown }[]
		}
		expect(keys()).toEqual(["signed-in-user", "language", "route-Logout"])
		expect(language.label).toBe("Language")
		expect(language.children.map(child => [child.key, child.label])).toEqual([
			["locale-en", "English"],
			["locale-it", "Italiano"],
			["locale-nl", "Nederlands"]
		])
		expect(language.children.map(child => !!child.icon)).toEqual([false, true, false])
	})

	it("stores a picked language and says so; a failure says that instead", async () => {
		store.isCustomerAdmin = false
		Object.assign(locales.value ?? {}, { locale: "en", available: ["en", "it"] })
		const choose = locales.value?.choose as ReturnType<typeof vi.fn>
		choose.mockResolvedValueOnce(undefined)
		mount(Avatar).getComponent(NDropdown).vm.$emit("select", "locale-it")
		await vi.waitFor(() => expect(message.success).toHaveBeenCalledWith("Language saved"))
		expect(choose).toHaveBeenCalledWith("it")
		expect(push).not.toHaveBeenCalled()

		choose.mockRejectedValueOnce(new Error("400"))
		mount(Avatar).getComponent(NDropdown).vm.$emit("select", "locale-it")
		await vi.waitFor(() => expect(message.error).toHaveBeenCalled())
	})

	it("ignores the current language and a code it doesn't ship", () => {
		store.isCustomerAdmin = false
		Object.assign(locales.value ?? {}, { locale: "en", available: ["en", "it"] })
		const wrapper = mount(Avatar)
		wrapper.getComponent(NDropdown).vm.$emit("select", "locale-en")
		wrapper.getComponent(NDropdown).vm.$emit("select", "locale-jp")
		expect(locales.value?.choose).not.toHaveBeenCalled()
	})
})
