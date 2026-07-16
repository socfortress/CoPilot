import type { Ref } from "vue"
import type { ApiError } from "@/types/common"
import axios from "axios"
import { useMessage } from "naive-ui"
import { computed, onScopeDispose, ref, watch } from "vue"
import { getApiErrorMessage } from "@/utils"

export interface EntityDetailsFetchResult<T> {
	entity: T | null
	message?: string
}

export interface EntityDetailsOptions<T, I> {
	/** The entity when the parent already has it (list rows pass it down). */
	entity: () => T | null | undefined
	/** The entity id when the component must fetch it itself (detail routes pass this). */
	id: () => I | null | undefined
	fetch: (id: I, signal: AbortSignal) => Promise<EntityDetailsFetchResult<T>>
	notFoundMessage?: string
	errorMessage?: string
	onLoaded?: (entity: T) => void
}

/**
 * Resolves an entity that is either handed down as a prop or fetched by id.
 *
 * Detail components are mounted both inside lists (entity already loaded) and on their own
 * bookmarkable route (only the id is known). This owns the fetch, the in-flight abort on id
 * change, and the not-found / error messaging so each component only supplies its fetcher.
 */
export function useEntityDetails<T, I = number>(options: EntityDetailsOptions<T, I>) {
	const message = useMessage()
	const loading = ref(false)
	const fetched = ref<T | null>(null) as Ref<T | null>

	let abortController: AbortController | null = null

	const entity = computed(() => options.entity() ?? fetched.value)

	function reset() {
		abortController?.abort()
		abortController = null
		fetched.value = null
		loading.value = false
	}

	function load(id: I) {
		abortController?.abort()
		abortController = new AbortController()
		loading.value = true

		options
			.fetch(id, abortController.signal)
			.then(result => {
				loading.value = false

				if (result.entity) {
					fetched.value = result.entity
					options.onLoaded?.(result.entity)
				} else {
					message.warning(result.message || options.notFoundMessage || "Entity not found.")
				}
			})
			.catch(err => {
				if (axios.isCancel(err)) return

				loading.value = false
				message.error(getApiErrorMessage(err as ApiError) || options.errorMessage || "Failed to load entity.")
			})
	}

	function reload() {
		const id = options.id()
		if (id !== null && id !== undefined) {
			load(id)
		}
	}

	watch(
		() => [options.entity(), options.id()] as const,
		([provided, id]) => {
			if (provided) {
				reset()
				return
			}

			if (id !== null && id !== undefined) {
				load(id)
				return
			}

			reset()
		},
		{ immediate: true }
	)

	onScopeDispose(() => abortController?.abort())

	return { loading, entity, reload }
}
