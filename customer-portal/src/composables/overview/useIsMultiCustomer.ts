import { computed } from "vue"
import { useAuthStore } from "@/stores/auth"

/**
 * Whether the user can see more than one customer. Customer codes are noise for a
 * single-tenant user and essential for everyone else, so views use this to decide
 * whether to print them.
 */
export function useIsMultiCustomer() {
	const authStore = useAuthStore()
	return computed(() => authStore.accessibleCustomerCodes.length > 1)
}
