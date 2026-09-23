import type { AiInsights } from "@/types/aiReports"
import type { Alert } from "@/types/alerts"
import type { Case } from "@/types/cases"
import type { ApiError } from "@/types/common"
import axios from "axios"
import { computed, reactive, ref, watch } from "vue"
import Api from "@/api"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import { getApiErrorMessage } from "@/utils"

/** How many items each "recent" list shows. The panels link to the full lists. */
export const RECENT_LIMIT = 6
const AI_RECENT_LIMIT = 3

export interface StatusCounts {
	total: number
	open: number
	in_progress: number
	closed: number
}

export interface AgentCounts {
	total: number
	online: number
	offline: number
	critical: number
}

export type OverviewSection = "alerts" | "cases" | "agents" | "ai"

function emptyCounts(): StatusCounts {
	return { total: 0, open: 0, in_progress: 0, closed: 0 }
}

/**
 * Everything the Overview renders, fetched in parallel and scoped to the global
 * customer filter.
 *
 * The alert and case *lists* already return their per-status counters, so one call
 * each covers both the posture numbers and the recent items — no separate stats
 * request. Every section loads, fails and reports independently: a failing agents
 * call must not blank the alerts the user came to see.
 */
export function useOverviewData() {
	const customerFilterStore = useCustomerFilterStore()

	const alerts = ref<Alert[]>([])
	const cases = ref<Case[]>([])
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
			Object.fromEntries(
				(Object.keys(loading) as OverviewSection[]).map(section => [section, !loaded.value && loading[section]])
			) as Record<OverviewSection, boolean>
	)

	let controller: AbortController | null = null

	async function run<T>(
		section: OverviewSection,
		request: () => Promise<T>,
		apply: (value: T) => void,
		signal: AbortSignal
	) {
		loading[section] = true
		errors[section] = null
		try {
			apply(await request())
		} catch (err) {
			if (axios.isCancel(err) || signal.aborted) return
			errors[section] = getApiErrorMessage(err as ApiError)
		} finally {
			if (!signal.aborted) loading[section] = false
		}
	}

	async function refresh() {
		controller?.abort()
		controller = new AbortController()
		const { signal } = controller
		const codes = customerFilterStore.queryCustomerCodes
		const page = { page: 1, pageSize: RECENT_LIMIT, order: "desc" as const }

		await Promise.all([
			run(
				"alerts",
				() => Api.alerts.getAlerts(page, signal, codes),
				res => {
					alerts.value = res.data.alerts ?? []
					alertCounts.value = {
						total: res.data.total ?? 0,
						open: res.data.open ?? 0,
						in_progress: res.data.in_progress ?? 0,
						closed: res.data.closed ?? 0
					}
				},
				signal
			),
			run(
				"cases",
				() => Api.cases.getCases(page, signal, codes),
				res => {
					cases.value = res.data.cases ?? []
					caseCounts.value = {
						total: res.data.total ?? 0,
						open: res.data.open ?? 0,
						in_progress: res.data.in_progress ?? 0,
						closed: res.data.closed ?? 0
					}
				},
				signal
			),
			run(
				"agents",
				() => Api.agents.getAgents(codes, signal),
				res => {
					const list = res.data.agents ?? []
					const online = list.filter(agent => agent.wazuh_agent_status === "active").length
					agentCounts.value = {
						total: list.length,
						online,
						offline: list.length - online,
						critical: list.filter(agent => agent.critical_asset).length
					}
				},
				signal
			),
			run(
				"ai",
				() => Api.aiReports.getInsights(codes, AI_RECENT_LIMIT, signal),
				res => {
					insights.value = res.data
				},
				signal
			)
		])

		if (!signal.aborted) {
			loaded.value = true
			lastUpdated.value = new Date()
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
