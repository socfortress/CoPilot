import type { Ref, WritableComputedRef } from "vue"
import type { SafeAny } from "@/types/utils"
import { onBeforeMount, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

/**
 * Synchronizes a ref with a key in the query string parameters.
 * @param key The query string key (e.g.: 'list_filters')
 * @param ref The ref to synchronize
 * @example
 * ```ts
 * useSyncUrlParams("list_filters", filters, {
 * 	onMountCheck(found) {
 * 		if (!found) {
 * 			resetFilters()
 * 		}
 * 	}
 * })
 * ```
 */
export function useSyncUrlParams(
	key: string,
	ref: WritableComputedRef<SafeAny, SafeAny> | Ref<SafeAny>,
	options?: {
		onMountCheck: (found: boolean) => void
	}
) {
	const route = useRoute()
	const router = useRouter()

	// Update the query string when ref changes
	watch(
		ref,
		val => {
			router.replace({ query: { ...route.query, [key]: JSON.stringify(val) } })
		},
		{ deep: true }
	)

	// On startup, if the query contains the key, update ref
	onBeforeMount(() => {
		if (route.query[key]) {
			const param = route.query[key].toString()
			const value = JSON.parse(`${param}`)

			if (value !== undefined) {
				ref.value = value
			}

			if (options?.onMountCheck && typeof options.onMountCheck === "function") {
				options.onMountCheck(true)
			}
		} else if (options?.onMountCheck && typeof options.onMountCheck === "function") {
			options.onMountCheck(false)
		}
	})
}
