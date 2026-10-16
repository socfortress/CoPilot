/**
 * The new-thread picker: "General (no customer data)" plus the caller's customers from
 * `GET /customers`, prefilled from the global sidebar filter when it names one of them.
 */
import type { SelectOption } from "naive-ui"
import { flushPromises, mount } from "@vue/test-utils"
import { NSelect } from "naive-ui"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { computed, ref } from "vue"
import TalonNewThread from "../TalonNewThread.vue"

const customerOptions = ref<SelectOption[]>([])
const globalCodes = ref<string[]>([])
const getMyCustomerAccess = vi.fn()

vi.mock("@/composables/useCustomerOptions", () => ({
	useCustomerOptions: () => ({
		options: computed(() => customerOptions.value),
		loading: computed(() => false),
		load: () => Promise.resolve(),
		reload: () => Promise.resolve()
	})
}))
vi.mock("@/stores/customer-filter", () => ({
	useCustomerFilterStore: () => ({
		get selectedCustomerCodes() {
			return globalCodes.value
		},
		isFiltering: false,
		liveSync: false
	})
}))
vi.mock("@/api", () => ({ default: { auth: { getMyCustomerAccess: () => getMyCustomerAccess() } } }))

const CUSTOMERS = [
	{ label: "Acme Corp (ACME)", value: "ACME" },
	{ label: "Globex (GLOBEX)", value: "GLOBEX" }
]

async function render() {
	const wrapper = mount(TalonNewThread, { global: { stubs: { Icon: true } } })
	await flushPromises()
	return wrapper
}

function select(wrapper: Awaited<ReturnType<typeof render>>) {
	return wrapper.getComponent(NSelect)
}

async function create(wrapper: Awaited<ReturnType<typeof render>>) {
	await wrapper.get('[data-testid="talon-v2-new-thread-create"]').trigger("click")
	return wrapper.emitted("create")?.at(-1)?.[0]
}

describe("talon v2 new-thread picker", () => {
	beforeEach(() => {
		customerOptions.value = CUSTOMERS
		globalCodes.value = []
		getMyCustomerAccess.mockReset().mockResolvedValue({ data: { customer_codes: ["ACME"], scope: "assigned" } })
	})

	it("lists General first, then the caller's customers", async () => {
		const wrapper = await render()
		const options = select(wrapper).props("options") as SelectOption[]
		expect(options.map(o => o.label)).toEqual(["General (no customer data)", "Acme Corp (ACME)", "Globex (GLOBEX)"])
	})

	it("defaults to General: a thread with no customer", async () => {
		const wrapper = await render()
		expect(await create(wrapper)).toEqual({ title: null, customer_code: null })
	})

	it("is prefilled from the global filter's first customer the caller can pick", async () => {
		globalCodes.value = ["NOT-MINE", "GLOBEX", "ACME"]
		const wrapper = await render()
		expect(select(wrapper).props("value")).toBe("GLOBEX")
		await wrapper.get('[data-testid="talon-v2-new-thread-title"] input').setValue("  ws-1  ")
		expect(await create(wrapper)).toEqual({ title: "ws-1", customer_code: "GLOBEX" })
	})

	it("stays General when the global filter names none of the caller's customers", async () => {
		globalCodes.value = ["NOT-MINE"]
		const wrapper = await render()
		expect(await create(wrapper)).toEqual({ title: null, customer_code: null })
	})

	it("a choice made in the picker is sent as it is", async () => {
		globalCodes.value = ["ACME"]
		const wrapper = await render()
		select(wrapper).vm.$emit("update:value", "__general__")
		await flushPromises()
		expect(await create(wrapper)).toEqual({ title: null, customer_code: null })
	})

	it("hints when the caller has no customers assigned", async () => {
		customerOptions.value = []
		getMyCustomerAccess.mockResolvedValue({ data: { customer_codes: [], scope: "unassigned" } })
		const wrapper = await render()
		expect(wrapper.find('[data-testid="talon-v2-new-thread-unassigned"]').exists()).toBe(true)
		expect((select(wrapper).props("options") as SelectOption[]).map(o => o.value)).toEqual(["__general__"])
	})

	it("shows a creation error as text", async () => {
		const wrapper = mount(TalonNewThread, {
			props: { error: "<b>customer_code is not a customer</b>" },
			global: { stubs: { Icon: true } }
		})
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-v2-new-thread-error"]').text()).toBe(
			"<b>customer_code is not a customer</b>"
		)
		expect(wrapper.find("b").exists()).toBe(false)
	})
})
