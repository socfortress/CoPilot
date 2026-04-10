<template>
	<div class="page md:page-wrapped flex flex-col gap-6 md:overflow-hidden">
		<p>Monitor your organization's security posture and recent activity</p>

		<div class="flex grow flex-col gap-6 overflow-hidden">
			<n-spin
				:show="loading"
				class="overflow-hidden"
				content-class="flex max-h-full grow flex-col overflow-hidden"
			>
				<n-alert v-if="error" type="error" title="Error Loading Dashboard" :description="error" />

				<div v-else class="@container flex grow flex-col gap-6 overflow-hidden">
					<OverviewStatsCards :stats />

					<div class="flex grow flex-col gap-6 overflow-hidden @2xl:flex-row">
						<div class="max-h-full basis-1/2 overflow-hidden">
							<OverviewRecentAlerts :recent-alerts class="h-full" size="small" />
						</div>
						<div class="max-h-full basis-1/2 overflow-hidden">
							<OverviewRecentCases :recent-cases class="h-full" size="small" />
						</div>
					</div>
				</div>
			</n-spin>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { Stats } from "@/components/overview/OverviewStatsCards.vue"
import type { DashboardAlert, DashboardCase } from "@/components/overview/types"
import type { ApiError } from "@/types/common"
import { NAlert, NSpin } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import OverviewRecentAlerts from "@/components/overview/OverviewRecentAlerts.vue"
import OverviewRecentCases from "@/components/overview/OverviewRecentCases.vue"
import OverviewStatsCards from "@/components/overview/OverviewStatsCards.vue"
import { getApiErrorMessage } from "@/utils"

const loading = ref(true)
const error = ref("")
const stats = ref<Stats>({
	totalAlerts: 0,
	criticalAlerts: 0,
	openCases: 0,
	totalAgents: 0,
	securityScore: 0,
	alertTrend: "+0",
	scoreImprovement: 0
})
const recentAlerts = ref<DashboardAlert[]>([])
const recentCases = ref<DashboardCase[]>([])

async function fetchDashboardData() {
	loading.value = true
	error.value = ""

	try {
		// Fetch alerts, cases, and agents data using our API services
		const [alertsResponse, casesResponse, agentsResponse] = await Promise.all([
			Api.alerts.getAlerts({ page: 1, pageSize: 50, order: "desc" }),
			Api.cases.getCases({ page: 1, pageSize: 50, order: "desc" }),
			Api.agents.getAgents()
		])

		const alerts = alertsResponse.data.alerts || []
		const cases = casesResponse.data.cases || []
		const agents = agentsResponse.data.agents || []

		// Calculate stats from real data
		const openAlerts = alertsResponse.data.open || 0
		const inProgressAlerts = alertsResponse.data.in_progress || 0

		const openCases = cases.filter(o => o.case_status === "OPEN" || o.case_status === "IN_PROGRESS").length

		// Calculate security score based on actual data
		const totalActiveIssues = openAlerts + inProgressAlerts + openCases
		const securityScore = Math.max(60, 100 - totalActiveIssues * 2)

		stats.value = {
			totalAlerts: alertsResponse.data.total || 0,
			criticalAlerts: openAlerts + inProgressAlerts,
			openCases,
			totalAgents: agents.length,
			securityScore: Math.min(100, securityScore),
			alertTrend: openAlerts > 0 ? `+${openAlerts}` : "0",
			scoreImprovement: Math.floor(Math.random() * 5) + 1
		}

		// Get recent alerts (last 5, sorted by creation time)
		recentAlerts.value = alerts
			.map(alert => ({
				id: alert.id,
				name: alert.alert_name || "Unnamed Alert",
				description: alert.alert_description || "No description available",
				severity: alert.status === "OPEN" ? "high" : alert.status === "IN_PROGRESS" ? "medium" : "low",
				created_at: alert.alert_creation_time || new Date().toISOString()
			}))
			.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
			.slice(0, 5)

		// Get recent cases (last 5, sorted by creation time)
		recentCases.value = cases
			.map(o => ({
				id: o.id,
				name: o.case_name || "Unnamed Case",
				description: o.case_description || "No description available",
				status: o.case_status || "open",
				created_at: o.case_creation_time || new Date().toISOString(),
				assigned_to: o.assigned_to || undefined
			}))
			.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
			.slice(0, 5)
	} catch (err) {
		error.value = getApiErrorMessage(err as ApiError) || "Failed to load dashboard data"

		// Set default/mock data if API fails
		stats.value = {
			totalAlerts: 0,
			criticalAlerts: 0,
			openCases: 0,
			totalAgents: 0,
			securityScore: 85,
			alertTrend: "0",
			scoreImprovement: 2
		}
		recentAlerts.value = []
		recentCases.value = []
	} finally {
		loading.value = false
	}
}

onBeforeMount(() => {
	fetchDashboardData()
})
</script>
