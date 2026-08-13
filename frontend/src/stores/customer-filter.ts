import { acceptHMRUpdate, defineStore } from "pinia"

/**
 * Global multi-customer filter for the analyst frontend.
 *
 * Empty `selectedCustomerCodes` means "all accessible customers". The backend
 * intersects requested codes with user_customer_access — stale codes never widen access.
 *
 * `liveSync` is a per-user preference (localStorage only, no API): when ON, every view
 * that consumes the global filter re-applies it to its own local filter as soon as the
 * global selection changes. When OFF, the global filter is only read once, when the view
 * mounts — the pre-existing behavior. Toggled from Profile → Settings.
 */
export const useCustomerFilterStore = defineStore("customer-filter", {
	state: () => ({
		selectedCustomerCodes: [] as string[],
		liveSync: true
	}),
	actions: {
		setSelected(codes: string[]) {
			this.selectedCustomerCodes = [...codes]
		},
		clear() {
			this.selectedCustomerCodes = []
		},
		setLiveSync(enabled: boolean) {
			this.liveSync = enabled
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
		pick: ["selectedCustomerCodes", "liveSync"]
	}
})

if (import.meta.hot) {
	import.meta.hot.accept(acceptHMRUpdate(useCustomerFilterStore, import.meta.hot))
}
