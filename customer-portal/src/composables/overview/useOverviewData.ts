import type { AiInsights } from "@/types/aiReports"
import type { ApiError } from "@/types/common"
import type { AgentCounts, OverviewAlert, OverviewCase, StatusCounts } from "@/types/portal"
import axios from "axios"
import { computed, reactive, ref, watch } from "vue"
import Api from "@/api"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import { getApiErrorMessage } from "@/utils"

/** How many items each "recent" list shows. The panels link to the full lists. */
export const RECENT_LIMIT = 6
const AI_RECENT_LIMIT = 3

export type OverviewSection = "alerts" | "cases" | "agents" | "ai"
const SECTIONS: OverviewSection[] = ["alerts", "cases", "agents", "ai"]

function emptyCounts(): StatusCounts {
	return { total: 0, open: 0, in_progress: 0, closed: 0 }
}

/**
 * Everything the Overview renders, from one `GET /customer_portal/overview` scoped to
 * the global customer filter.
 *
 * The backend loads each section on its own and reports a failure on that section
 * only, so a failing agents count still leaves the alerts the user came to see. A
 * failure of the request itself is reported on every section.
 */
export function useOverviewData() {
	const customerFilterStore = useCustomerFilterStore()

	const alerts = ref<OverviewAlert[]>([])
	const cases = ref<OverviewCase[]>([])
	const alertCounts = ref<StatusCounts>(emptyCounts())
	const caseCounts = ref<StatusCounts>(emptyCounts())
	const agentCounts = ref<AgentCounts>({ total: 0, online: 0, offline: 0, critical: 0 })
	const insights = ref<AiInsights>({ total_reports: 0, severity_counts: {}, recent: [] })

	const loading = reactive<Record<OverviewSection, boolean>>({
		alerts: false,
		cases: false,
		agents: false,
		ai: false
	})
	const errors = reactive<Record<OverviewSection, string | null>>({
		alerts: null,
		cases: null,
		agents: null,
		ai: null
	})
	/** `false` until the first load settles, so the page can show skeletons instead of zeros. */
	const loaded = ref(false)
	const lastUpdated = ref<Date | null>(null)

	const isRefreshing = computed(() => Object.values(loading).some(Boolean))

	/**
	 * Placeholders belong to the first load only: a refresh keeps the current numbers
	 * on screen instead of flashing skeletons over them.
	 */
	const showSkeleton = computed(
		() =>
			Object.fromEntries(SECTIONS.map(section => [section, !loaded.value && loading[section]])) as Record<
				OverviewSection,
				boolean
			>
	)

	let controller: AbortController | null = null

	function setAll<T>(target: Record<OverviewSection, T>, value: T) {
		for (const section of SECTIONS) target[section] = value
	}

	async function refresh() {
		controller?.abort()
		controller = new AbortController()
		const { signal } = controller

		setAll(loading, true)
		setAll(errors, null)

		try {
			const { data } = await Api.portal.overview({
				recentLimit: RECENT_LIMIT,
				aiLimit: AI_RECENT_LIMIT,
				customerCodes: customerFilterStore.queryCustomerCodes,
				signal
			})

			alerts.value = data.alerts.recent
			alertCounts.value = data.alerts.counts
			cases.value = data.cases.recent
			caseCounts.value = data.cases.counts
			const { error: agentsError, ...agents } = data.agents
			agentCounts.value = agents
			const { error: aiError, ...ai } = data.ai
			insights.value = ai

			errors.alerts = data.alerts.error
			errors.cases = data.cases.error
			errors.agents = agentsError
			errors.ai = aiError
		} catch (err) {
			if (axios.isCancel(err) || signal.aborted) return
			setAll(errors, getApiErrorMessage(err as ApiError))
		} finally {
			if (!signal.aborted) {
				setAll(loading, false)
				loaded.value = true
				lastUpdated.value = new Date()
			}
		}
	}

	// The global filter is a multi-select that rewrites the array on each change.
	watch(() => customerFilterStore.selectedCustomerCodes, refresh)

	return {
		alerts,
		cases,
		alertCounts,
		caseCounts,
		agentCounts,
		insights,
		loading,
		errors,
		loaded,
		showSkeleton,
		lastUpdated,
		isRefreshing,
		refresh
	}
}
