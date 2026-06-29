import { computed } from "vue"
import { useCustomerFilterStore } from "@/stores/customer-filter.ts"

export function useGlobalCustomerFilter() {
	const store = useCustomerFilterStore()
	const globalCustomerCodes = computed(() => store.selectedCustomerCodes)
	const globalCustomerCode = computed(() => globalCustomerCodes.value?.[0] || null)
	const isFiltering = computed(() => store.isFiltering)

	function applyGlobalCustomerPrefill(
		customerFilterType: string,
		filters: Record<string, unknown>,
		options?: {
			availableCustomerCodes?: string[]
			multiple?: boolean
		}
	) {
		const codes = options?.availableCustomerCodes?.length
			? globalCustomerCodes.value.filter(c => (options.availableCustomerCodes || []).includes(c))
			: globalCustomerCodes.value

		if (!filters[customerFilterType]) {
			filters[customerFilterType] = options?.multiple ? codes : codes[0]
		}

		return filters
	}

	function getAvailableGlobalCustomerValue(availableCustomerCodes: string[], multiple: true): string[]
	function getAvailableGlobalCustomerValue(availableCustomerCodes: string[], multiple?: false): string | undefined
	function getAvailableGlobalCustomerValue(
		availableCustomerCodes: string[],
		multiple?: boolean
	): string[] | string | undefined {
		const codes = globalCustomerCodes.value.filter(c => availableCustomerCodes.includes(c))
		return multiple ? codes : codes[0]
	}

	return {
		globalCustomerCodes,
		globalCustomerCode,
		isFiltering,
		applyGlobalCustomerPrefill,
		getAvailableGlobalCustomerValue
	}
}
