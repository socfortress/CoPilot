import type { ApiError } from "@/types/common"
import type { SidebarContextResponse, SidebarHealthIndicator } from "@/types/sidebar-context"
import { useIntervalFn } from "@vueuse/core"
import { computed, onMounted, ref, shallowRef } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"

const REFRESH_INTERVAL_MS = 5 * 60 * 1000

export function useSidebarContext() {
	const context = shallowRef<SidebarContextResponse | null>(null)
	const loading = ref(false)
	const loadError = ref<string | null>(null)

	async function refresh() {
		loading.value = true
		loadError.value = null

		try {
			const response = await Api.sidebarContext.getSidebarContext()
			if (response.data.success) {
				context.value = response.data
			} else {
				loadError.value = response.data.message || "Failed to load sidebar context"
			}
		} catch (err) {
			loadError.value = getApiErrorMessage(err as ApiError) || "Failed to load sidebar context"
		} finally {
			loading.value = false
		}
	}

	onMounted(() => {
		void refresh()
	})

	useIntervalFn(refresh, REFRESH_INTERVAL_MS)

	const indicators = computed<SidebarHealthIndicator[]>(() => context.value?.indicators ?? [])

	const issueIndicators = computed(() => indicators.value.filter(indicator => indicator.status !== "ok"))

	const overallStatus = computed<"ok" | "warning" | "error">(() => {
		if (issueIndicators.value.some(indicator => indicator.status === "error")) {
			return "error"
		}
		if (issueIndicators.value.length > 0) {
			return "warning"
		}
		return "ok"
	})

	return {
		context,
		loading,
		loadError,
		indicators,
		issueIndicators,
		overallStatus,
		refresh
	}
}
