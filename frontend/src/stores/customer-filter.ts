import { acceptHMRUpdate, defineStore } from "pinia"

/**
 * Global multi-customer filter for the analyst frontend.
 *
 * Empty `selectedCustomerCodes` means "all accessible customers". The backend
 * intersects requested codes with user_customer_access — stale codes never widen access.
 */
export const useCustomerFilterStore = defineStore("customer-filter", {
	state: () => ({
		selectedCustomerCodes: [] as string[]
	}),
	actions: {
		setSelected(codes: string[]) {
			this.selectedCustomerCodes = [...codes]
		},
		clear() {
			this.selectedCustomerCodes = []
		},
		/** Drop any persisted selection the current user can no longer access. */
		pruneToAccessible(accessibleCodes: string[]) {
			if (!this.selectedCustomerCodes.length) {
				return
			}
			this.selectedCustomerCodes = this.selectedCustomerCodes.filter(code => accessibleCodes.includes(code))
		}
	},
	getters: {
		isFiltering(state): boolean {
			return !!state.selectedCustomerCodes.length
		}
	},
	persist: {
		pick: ["selectedCustomerCodes"]
	}
})

if (import.meta.hot) {
	import.meta.hot.accept(acceptHMRUpdate(useCustomerFilterStore, import.meta.hot))
}
