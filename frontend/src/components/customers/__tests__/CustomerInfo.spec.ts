import type { Customer } from "@/types/customers"
import { flushPromises, mount } from "@vue/test-utils"
import { NDialogProvider, NMessageProvider } from "naive-ui"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import CustomerInfo from "../CustomerInfo.vue"

const customers = vi.hoisted(() => ({ deleteCustomer: vi.fn() }))
vi.mock("@/api", () => ({ default: { customers } }))
vi.mock("../CustomerForm.vue", () => ({
	default: defineComponent({ setup: () => () => h("form", { "data-testid": "customer-form" }) })
}))

function customer(extra: Partial<Customer> = {}): Customer {
	return {
		customer_code: "ACME",
		customer_name: "Acme Rome",
		contact_first_name: "Giulia",
		contact_last_name: "Bianchi",
		parent_customer_code: null,
		phone: "+39 06 1234 5678",
		address_line1: "Via del Corso 1",
		address_line2: "",
		city: "Roma",
		state: "RM",
		postal_code: "00186",
		country: "Italy",
		customer_type: "MSSP",
		logo_file: "",
		is_provisioned: false,
		...extra
	}
}

function render(value: Customer) {
	const onDelete = vi.fn()
	const wrapper = mount(
		defineComponent({
			setup: () => () =>
				h(NMessageProvider, null, () =>
					h(NDialogProvider, null, () => h(CustomerInfo, { customer: value, onDelete })))
		}),
		{ attachTo: document.body }
	)
	return { wrapper, onDelete }
}

/** The Info tab: who the customer is, its fields by purpose, and deleting apart from editing. */
describe("customerInfo", () => {
	beforeEach(() => {
		document.body.innerHTML = ""
		customers.deleteCustomer.mockReset()
	})

	it("leads with the name, the code, the type and whether it is provisioned", () => {
		const { wrapper } = render(customer())
		const header = wrapper.get("[data-testid=customer-info-header]")
		expect(header.text()).toContain("Acme Rome")
		expect(wrapper.get("[data-testid=customer-info-code]").text()).toBe("ACME")
		expect(wrapper.get("[data-testid=customer-info-type]").text()).toBe("MSSP")
		expect(wrapper.get("[data-testid=customer-info-provisioned]").text()).toBe("Not provisioned")
		expect(render(customer({ is_provisioned: true })).wrapper.get("[data-testid=customer-info-provisioned]").text()).toBe(
			"Provisioned"
		)
	})

	it("groups the fields: a joined contact name, one formatted address, and Not set where empty", () => {
		const { wrapper } = render(customer())
		const contact = wrapper.get("[data-testid=customer-info-contact]").text()
		expect(contact).toContain("Giulia Bianchi")
		expect(contact).toContain("+39 06 1234 5678")
		const address = wrapper.get("[data-testid=customer-info-address] dd")
		expect(address.text()).toBe("Via del Corso 1\n00186 Roma\nRM, Italy")
		expect(wrapper.get("[data-testid=customer-info-organization]").text()).toContain("Not set")
	})

	it("opens the form from Edit", async () => {
		const { wrapper } = render(customer())
		await wrapper.get("[data-testid=customer-info-edit]").trigger("click")
		expect(wrapper.find("[data-testid=customer-form]").exists()).toBe(true)
	})

	it("deletes only once confirmed, naming the customer as text", async () => {
		customers.deleteCustomer.mockResolvedValue({ data: { success: true } })
		const { wrapper, onDelete } = render(customer({ customer_name: "<img src=x>" }))
		await wrapper.get("[data-testid=customer-info-delete]").trigger("click")
		await flushPromises()
		const dialog = document.querySelector(".n-dialog")
		expect(dialog?.querySelector("img")).toBeNull()
		expect(dialog?.textContent).toContain("<img src=x>")
		expect(customers.deleteCustomer).not.toHaveBeenCalled()
		const confirm = [...document.querySelectorAll<HTMLButtonElement>(".n-dialog button")].find(b =>
			b.textContent?.includes("Delete customer")
		)
		confirm?.click()
		await flushPromises()
		expect(customers.deleteCustomer).toHaveBeenCalledWith("ACME")
		expect(onDelete).toHaveBeenCalled()
		wrapper.unmount()
	})
})
