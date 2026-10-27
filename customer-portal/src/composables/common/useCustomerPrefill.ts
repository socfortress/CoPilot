import { computed } from "vue"
import { useCustomers } from "@/composables/common/useCustomers"
import { useAuthStore } from "@/stores/auth"
import { useCustomerFilterStore } from "@/stores/customerFilter"

/**
 * Picks the customer a creation form (case, report, …) should be seeded with.
 *
 * A portal user may be scoped to several customers, and `customer_codes[0]` from the
 * JWT is an arbitrary one — using it silently files the new object under the wrong
 * tenant. The rule is: the global customer filter wins when it resolves to exactly one
 * customer; otherwise a user with a single accessible customer gets that one; anyone
 * else must choose explicitly (`null`). Forms should render the select only when
 * `hasMultipleCustomers` is true and treat the field as required.
 *
 * `writable`: the form files something, so only the customers whose data the user may change
 * count (#1312); a read-only customer is never offered nor seeded.
 */
export function useCustomerPrefill(options: { writable?: boolean } = {}) {
	const authStore = useAuthStore()
	const customerFilterStore = useCustomerFilterStore()

	const { customerOptions, filterCustomer, renderCustomerLabel } = useCustomers(options)
	const codes = computed(() =>
		options.writable ? authStore.writableCustomers.map(customer => customer.customer_code) : authStore.accessibleCustomerCodes
	)
	const hasMultipleCustomers = computed(() => codes.value.length > 1)

	function initialCustomerCode(): string | null {
		const accessible = codes.value
		const selected = customerFilterStore.selectedCustomerCodes.filter(code => accessible.includes(code))

		if (selected.length === 1) return selected[0]
		if (accessible.length === 1) return accessible[0]
		return null
	}

	return { customerOptions, filterCustomer, renderCustomerLabel, hasMultipleCustomers, initialCustomerCode }
}
