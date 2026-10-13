import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it } from "vitest"
import { h } from "vue"
import CustomerName from "@/components/common/CustomerName.vue"
import { useAuthStore } from "@/stores/auth"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import { useCustomers } from "../useCustomers"

function withCustomers(customers: [string, string][]) {
	const store = useAuthStore()
	store.customers = customers.map(([customer_code, customer_name]) => ({ customer_code, customer_name }))
	return store
}

describe("useCustomers (#1243)", () => {
	beforeEach(() => setActivePinia(createPinia()))

	it("offers each customer by name, with the code as the value sent", () => {
		withCustomers([
			["ACME", "Acme Rome"],
			["BETA", "Beta Milan"]
		])
		expect(useCustomers().customerOptions.value).toEqual([
			{ label: "Acme Rome", value: "ACME" },
			{ label: "Beta Milan", value: "BETA" }
		])
	})

	it("finds a customer by its name or by its code, case-insensitively", () => {
		const { filterCustomer } = useCustomers()
		const option = { label: "Acme Rome", value: "ACME01" }
		expect(filterCustomer("rome", option)).toBe(true)
		expect(filterCustomer("acme01", option)).toBe(true)
		expect(filterCustomer("  ", option)).toBe(true)
		expect(filterCustomer("milan", option)).toBe(false)
	})

	it("renders the code beside the name, and only the name when they are the same", () => {
		const { renderCustomerLabel } = useCustomers()
		expect(renderCustomerLabel({ label: "ACME", value: "ACME" })).toBe("ACME")

		const wrapper = mount({ render: () => renderCustomerLabel({ label: "Acme Rome", value: "ACME" }) })
		expect(wrapper.text()).toContain("Acme Rome")
		expect(wrapper.find("[data-testid=customer-option-code]").text()).toBe("ACME")
	})

	it("customerName falls back to the code", () => {
		withCustomers([["ACME", "Acme Rome"]])
		const { customerName } = useCustomers()
		expect(customerName("ACME")).toBe("Acme Rome")
		expect(customerName("GONE")).toBe("GONE")
	})
})

describe("customerName", () => {
	beforeEach(() => setActivePinia(createPinia()))

	it("shows the name with the code beside it", () => {
		withCustomers([["ACME", "Acme Rome"]])
		const wrapper = mount({ render: () => h(CustomerName, { code: "ACME" }) })
		expect(wrapper.text()).toBe("Acme RomeACME")
		expect(wrapper.find("[data-testid=customer-name]").attributes("title")).toBe("ACME")
	})

	it("shows only the code when no name is known, and a dash for nothing", () => {
		expect(mount({ render: () => h(CustomerName, { code: "GONE" }) }).text()).toBe("GONE")
		expect(mount({ render: () => h(CustomerName, { code: null }) }).text()).toBe("—")
	})
})

describe("customer filter: pruning to the accessible customers", () => {
	beforeEach(() => setActivePinia(createPinia()))

	it("drops what the user can no longer see", () => {
		const filter = useCustomerFilterStore()
		filter.setSelected(["ACME", "GONE"])
		filter.pruneToAccessible(["ACME"])
		expect(filter.selectedCustomerCodes).toEqual(["ACME"])
	})

	it("leaves the selection untouched when nothing is dropped: every list watches it", () => {
		const filter = useCustomerFilterStore()
		filter.setSelected(["ACME"])
		const before = filter.selectedCustomerCodes
		filter.pruneToAccessible(["ACME", "BETA"])
		expect(filter.selectedCustomerCodes).toBe(before)
	})
})
