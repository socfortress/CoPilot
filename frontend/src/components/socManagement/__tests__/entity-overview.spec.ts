import type { PropType } from "vue"
import type { OverviewTarget } from "../EntityOverviewModal.vue"
import type { User } from "@/types/user"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"
import UserDetailsByUsername from "@/components/users/UserDetailsByUsername.vue"
import EntityOverviewModal from "../EntityOverviewModal.vue"

const getUsers = vi.fn()
vi.mock("@/api", () => ({ default: { users: { getUsers: (...args: unknown[]) => getUsers(...args) } } }))

// The details pages themselves are covered where they live; here they only need to
// receive the right key. `__esModule` because the modal loads them lazily, and Vue reads
// a lazy component's `default` only from something that says it is an ES module.
vi.mock("@/components/customers/CustomerDetails.vue", () => ({
	__esModule: true,
	default: defineComponent({
		name: "CustomerDetails",
		props: { customerCode: String },
		emits: ["loaded", "delete"],
		setup: props => () => h("div", { "data-testid": "customer-details" }, props.customerCode)
	})
}))
vi.mock("@/components/users/UserDetails.vue", () => ({
	__esModule: true,
	default: defineComponent({
		name: "UserDetails",
		props: { user: Object },
		emits: ["deleted"],
		setup: props => () => h("div", { "data-testid": "user-details" }, (props.user as User | undefined)?.username)
	})
}))

const user = (username: string, id = 1): User => ({ id, username, email: `${username}@example.com`, role_name: "analyst" })

beforeEach(() => {
	setActivePinia(createPinia())
	getUsers.mockReset()
})

function inProvider(component: unknown, props: Record<string, unknown>) {
	return mount(
		defineComponent({ setup: () => () => h(NMessageProvider, null, { default: () => h(component as never, props) }) }),
		{ attachTo: document.body }
	)
}

describe("userDetailsByUsername", () => {
	it("shows the user whose name matches exactly, not one that merely contains it", async () => {
		getUsers.mockResolvedValue({ data: { users: [user("anastasia", 2), user("ana", 3)] } })
		const wrapper = inProvider(UserDetailsByUsername, { username: "ana" })
		await flushPromises()
		expect(getUsers).toHaveBeenCalledWith({ search: "ana", limit: 50 }, expect.any(AbortSignal))
		expect(wrapper.get("[data-testid=user-details]").text()).toBe("ana")
		wrapper.unmount()
	})

	it("says so when nobody has that name any more, or the lookup fails", async () => {
		getUsers.mockResolvedValue({ data: { users: [user("anastasia")] } })
		const missing = inProvider(UserDetailsByUsername, { username: "ana" })
		await flushPromises()
		expect(missing.get("[data-testid=user-details-missing]").text()).toContain('No CoPilot user is called "ana"')
		missing.unmount()

		getUsers.mockImplementation(() => Promise.reject(new Error("boom")))
		const failed = inProvider(UserDetailsByUsername, { username: "ana" })
		await flushPromises()
		expect(failed.get("[data-testid=user-details-missing]").text()).toContain("Could not load this user")
		failed.unmount()
	})
})

describe("entityOverviewModal", () => {
	it("is closed without a target, opens the customer's or the user's overview, and links its page", async () => {
		getUsers.mockResolvedValue({ data: { users: [user("ana")] } })
		const Host = defineComponent({
			props: { target: { type: Object as PropType<OverviewTarget | null>, default: null } },
			setup: props => () => h(NMessageProvider, null, { default: () => h(EntityOverviewModal, { target: props.target }) })
		})
		const blank = { render: () => null }
		const appRouter = createRouter({
			history: createMemoryHistory(),
			routes: [
				{ path: "/", component: blank },
				{ path: "/customers/:code", name: "Customer", component: blank },
				{ path: "/users/:id", name: "UserView", component: blank }
			]
		})
		await appRouter.push("/")
		const wrapper = mount(Host, { props: { target: null }, attachTo: document.body, global: { plugins: [appRouter] } })
		await flushPromises()
		expect(document.querySelector("[data-testid=entity-overview-modal]")).toBeNull()
		const pageLink = () => document.querySelector("[data-testid=modal-page-button]")?.getAttribute("href")

		await wrapper.setProps({ target: { kind: "customer", key: "ACME" } })
		await flushPromises()
		expect(document.body.textContent).toContain("Customer · ACME")
		expect(document.querySelector("[data-testid=customer-details]")?.textContent).toBe("ACME")
		expect(pageLink()).toBe("/customers/ACME")

		await wrapper.setProps({ target: { kind: "user", key: "ana" } })
		await flushPromises()
		expect(document.body.textContent).toContain("User · ana")
		expect(document.querySelector("[data-testid=user-details]")?.textContent).toBe("ana")
		expect(pageLink()).toBe("/users/1") // addressed by id, known once the user loaded
		wrapper.unmount()
	})
})
