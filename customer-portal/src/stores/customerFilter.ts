import { acceptHMRUpdate, defineStore } from "pinia"

/**
 * Holds the Customer Portal's global multi-customer filter.
 *
 * An empty `selectedCustomerCodes` means "All accessible customers" (the default,
 * preserving the previous behaviour). When one or more codes are selected, portal
 * data is scoped to that subset. The backend always intersects the requested codes
 * with the user's accessible customers, so a stale/invalid code here can never widen
 * access — at worst it is ignored.
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
		/** Drop any selected codes the user no longer has access to. */
		pruneToAccessible(accessibleCodes: string[]) {
			const kept = this.selectedCustomerCodes.filter(code => accessibleCodes.includes(code))
			// Replace the selection only when something was dropped: every list watches it,
			// and a new array with the same codes would reload them all for nothing.
			if (kept.length !== this.selectedCustomerCodes.length) {
				this.selectedCustomerCodes = kept
			}
		}
	},
	getters: {
		isFiltering(state): boolean {
			return state.selectedCustomerCodes.length > 0
		},
		/**
		 * The value to pass to customer-scoped API calls: the selected subset, or
		 * `undefined` when nothing is selected (meaning "all accessible").
		 */
		queryCustomerCodes(state): string[] | undefined {
			return state.selectedCustomerCodes.length ? state.selectedCustomerCodes : undefined
		}
	},
	persist: {
		pick: ["selectedCustomerCodes"]
	}
})

if (import.meta.hot) {
	import.meta.hot.accept(acceptHMRUpdate(useCustomerFilterStore, import.meta.hot))
}
