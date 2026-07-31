import type { WatchStopHandle } from "vue"
import { watchDebounced } from "@vueuse/core"
import { computed } from "vue"
import { useCustomerFilterStore } from "@/stores/customer-filter"

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

		if (!filters[customerFilterType] || (options?.multiple && !(filters[customerFilterType] as string[])?.length)) {
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

	/**
	 * Live-sync hook for views that own a local customer filter.
	 *
	 * Fires `callback` with the new selection every time the global filter changes, but ONLY
	 * while the user preference is enabled (Profile → Settings → "Live sync"). With the
	 * preference off the callback never runs and the view keeps its mount-time-only behavior.
	 *
	 * The contract every call site implements: **the global filter wins over the local one**,
	 * because changing the sidebar select is an explicit user action. Views whose local filter
	 * is optional clear it when the global selection is emptied; views that cannot render
	 * without a customer keep the current one and say so in a one-line comment.
	 *
	 * Debounced because the sidebar multi-select writes the store on every tag add/remove —
	 * without it, scoping to three customers would fire three rounds of refetches. Kept short
	 * (150ms) because some views debounce their own fetch on top of this one and the two delays
	 * stack: `caseTemplates/CaseTemplatesTable.vue` adds another 400ms.
	 *
	 * Must be called during component setup so the watcher is disposed with the view.
	 */
	function onGlobalCustomerFilterChange(callback: (codes: string[]) => void): WatchStopHandle {
		return watchDebounced(
			// join() so the watcher compares content, not the array identity Pinia hands back
			() => globalCustomerCodes.value.join(","),
			() => {
				if (store.liveSync) {
					callback([...globalCustomerCodes.value])
				}
			},
			{ debounce: 150 }
		)
	}

	return {
		globalCustomerCodes,
		globalCustomerCode,
		isFiltering,
		applyGlobalCustomerPrefill,
		getAvailableGlobalCustomerValue,
		onGlobalCustomerFilterChange
	}
}
