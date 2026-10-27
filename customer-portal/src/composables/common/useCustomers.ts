import type { SelectOption } from "naive-ui"
import { computed, h } from "vue"
import { useAuthStore } from "@/stores/auth"

/**
 * The user's customers as the portal shows them: by name, with the code as the value
 * every API call sends. One place for the picker options, the label rendering and the
 * lookup, so a customer reads the same in the filter, the forms and the pages.
 */
export function useCustomers(options: { writable?: boolean } = {}) {
	const authStore = useAuthStore()

	// A form that files something offers only the customers whose data the user may change (#1312).
	const customerOptions = computed<SelectOption[]>(() =>
		(options.writable ? authStore.writableCustomers : authStore.accessibleCustomers).map(customer => ({
			label: customer.customer_name,
			value: customer.customer_code
		}))
	)

	/** A customer's name, or its code when the name is not known. */
	function customerName(code: string | null | undefined): string {
		return authStore.customerName(code)
	}

	/** For `n-select`'s `filter`: a customer is found by its name or by its code. */
	function filterCustomer(pattern: string, option: SelectOption): boolean {
		const needle = pattern.trim().toLowerCase()
		if (!needle) return true
		return [option.label, option.value].some(text =>
			String(text ?? "")
				.toLowerCase()
				.includes(needle)
		)
	}

	/** For `n-select`'s `render-label`: the name, with the code beside it when they differ. */
	function renderCustomerLabel(option: SelectOption) {
		const name = String(option.label ?? "")
		const code = String(option.value ?? "")
		if (!code || code === name) return name
		return h("span", { class: "inline-flex items-baseline gap-2" }, [
			h("span", name),
			h("span", { class: "text-secondary font-mono text-xs", "data-testid": "customer-option-code" }, code)
		])
	}

	return { customerOptions, customerName, filterCustomer, renderCustomerLabel }
}
