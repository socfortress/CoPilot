import { computed } from "vue"
import { useCustomerFilterStore } from "@/stores/customerFilter"

/** Single-code default for single-select page filters (empty when global has 0 or 2+ codes). */
export function globalCustomerSingleDefault(): string | null {
	const codes = useCustomerFilterStore().selectedCustomerCodes
	return codes.length === 1 ? codes[0] : null
}

/** Push a customer filter row when global has exactly one code and none is set yet. */
export function applyGlobalCustomerPrefill<T extends { type: string; value: unknown }>(
	customerFilterType: string,
	filters: T[]
): boolean {
	if (filters.some(f => f.type === customerFilterType && f.value)) {
		return false
	}
	const code = globalCustomerSingleDefault()
	if (!code) {
		return false
	}
	filters.push({ type: customerFilterType, value: code } as T)
	return true
}

export function useGlobalCustomerFilter() {
	const store = useCustomerFilterStore()

	const queryCustomerCodes = computed(() => store.queryCustomerCodes)
	const isFiltering = computed(() => store.isFiltering)

	function filterByGlobal<T extends { customer_code: string }>(items: T[]): T[] {
		if (!store.selectedCustomerCodes.length) {
			return items
		}
		return items.filter(i => store.selectedCustomerCodes.includes(i.customer_code))
	}

	return { store, queryCustomerCodes, isFiltering, filterByGlobal, globalCustomerSingleDefault }
}
