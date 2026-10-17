/**
 * The picker's customers are the signed-in user's own (`GET /customers` is scoped to the caller).
 * `useCustomerOptions` keeps them module-level, so logout must clear them: user B, signing in on
 * the same tab after user A, is offered only B's customers, never A's.
 */
import type { SelectOption } from "naive-ui"
import { flushPromises, mount } from "@vue/test-utils"
import { NSelect } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { useCustomerOptions } from "@/composables/useCustomerOptions"
import { useAuthStore } from "@/stores/auth"
import TalonNewThread from "../TalonNewThread.vue"

const getCustomers = vi.fn()

vi.mock("@/api", () => ({
	default: {
		customers: { getCustomers: (...a: unknown[]) => getCustomers(...a) },
		auth: { getMyCustomerAccess: async () => ({ data: { customer_codes: [], scope: "assigned" } }) },
		talonV2: { getAvailability: async () => ({ data: { enabled: false } }) }
	}
}))

function customers(...codes: string[]) {
	return { data: { customers: codes.map(code => ({ customer_code: code, customer_name: code.toLowerCase() })) } }
}

async function pickerOptions() {
	const wrapper = mount(TalonNewThread, { global: { stubs: { Icon: true } } })
	await flushPromises()
	const values = (wrapper.getComponent(NSelect).props("options") as SelectOption[]).map(o => o.value)
	wrapper.unmount()
	return values
}

describe("talon v2 picker across a logout", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		getCustomers.mockReset()
	})

	it("user B sees only their own customers after user A logs out", async () => {
		getCustomers.mockResolvedValueOnce(customers("ACME", "GLOBEX"))
		expect(await pickerOptions()).toEqual(["__general__", "ACME", "GLOBEX"])

		useAuthStore().setLogout()
		expect(useCustomerOptions().options.value).toEqual([])

		getCustomers.mockResolvedValueOnce(customers("INITECH"))
		expect(await pickerOptions()).toEqual(["__general__", "INITECH"])
	})

	it("an answer for the previous user that lands after logout is dropped", async () => {
		let answerForA: (value: unknown) => void = () => {}
		getCustomers.mockReturnValueOnce(new Promise(resolve => (answerForA = resolve)))
		const pending = useCustomerOptions().reload()

		useAuthStore().setLogout()
		answerForA(customers("ACME"))
		await pending
		expect(useCustomerOptions().options.value).toEqual([])
	})

	it("the picker asks again each time it opens", async () => {
		getCustomers.mockResolvedValue(customers("ACME"))
		await pickerOptions()
		await pickerOptions()
		expect(getCustomers).toHaveBeenCalledTimes(2)
	})
})
