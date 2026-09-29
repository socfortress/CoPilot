import type { Ref, WatchSource } from "vue"
import { watch } from "vue"

/**
 * Loads a server-paginated list exactly once per change.
 *
 * - on mount;
 * - when `page` changes;
 * - when any `resetOn` source changes (page size, filters, the global customer
 *   filter): back to page 1 first, then one load.
 *
 * Lists used to watch the page and the filters separately, both `immediate`, so every
 * mount loaded twice; a 400 ms debounce hid the duplicate but delayed every click as
 * well. Debounce only what is typed, in the caller (`refDebounced`), before it gets here.
 */
export function usePaginatedLoad(options: { page: Ref<number>; resetOn: WatchSource[]; load: () => unknown }) {
	const { page, resetOn, load } = options

	watch(
		[page, ...resetOn],
		(current, previous) => {
			const resetRequested = previous !== undefined && current.slice(1).some((value, index) => value !== previous[index + 1])

			// Returning to page 1 changes `page`, which runs this watcher again and loads.
			if (resetRequested && page.value !== 1) {
				page.value = 1
				return
			}
			load()
		},
		{ immediate: true }
	)
}
