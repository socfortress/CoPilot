import type { Ref } from "vue"
import type { SocAttentionQuery, SocScopeQuery } from "@/api/endpoints/soc-management"
import type { ApiError } from "@/types/common"
import type { AttentionItem } from "@/types/soc-management"
import { computed, shallowRef, watch } from "vue"
import Api from "@/api"

export const ATTENTION_LIMIT = 200

/**
 * The full "needs attention" list for the Workload tab — the dashboard carries only
 * its top ten. Reloads when the scope or the entity/state filter changes, aborting
 * the request it supersedes.
 */
export function useAttention(scope: Ref<SocScopeQuery>, filter: Ref<Pick<SocAttentionQuery, "entity" | "state">>) {
	const items = shallowRef<AttentionItem[]>([])
	const total = shallowRef(0)
	const loading = shallowRef(false)
	const error = shallowRef<ApiError | null>(null)
	let controller: AbortController | null = null

	async function load() {
		controller?.abort()
		const current = new AbortController()
		controller = current
		loading.value = true
		error.value = null
		try {
			const response = await Api.socManagement.getAttention(
				{ ...scope.value, ...filter.value, limit: ATTENTION_LIMIT },
				current.signal
			)
			if (controller !== current) return
			items.value = response.data.items
			total.value = response.data.total
		} catch (err) {
			const name = (err as { name?: string })?.name
			if (controller === current && name !== "CanceledError" && name !== "AbortError")
				error.value = err as ApiError
		} finally {
			if (controller === current) loading.value = false
		}
	}

	watch(() => JSON.stringify([scope.value, filter.value]), load, { immediate: true })

	return {
		items: computed(() => items.value),
		total: computed(() => total.value),
		loading: computed(() => loading.value),
		error: computed(() => error.value),
		reload: load
	}
}
