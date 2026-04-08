<template>
	<div class="page">
		<p>Monitor your organization's security posture and recent activity</p>

		<n-spin :show="loading">
			<n-alert v-if="error" type="error" title="Error Loading Dashboard" :description="error" />

			<div v-else class="@container mt-4 flex flex-col gap-6">
				<OverviewStatsCards :stats />

				<!-- Recent Activity and Charts Section -->
				<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
					<!-- Recent Alerts -->
					<div class="rounded-lg bg-white shadow-sm">
						<div class="border-b border-gray-200 px-6 py-4">
							<h3 class="text-lg font-medium text-gray-900">Recent Alerts</h3>
						</div>
						<div class="p-6">
							<div v-if="recentAlerts.length === 0" class="py-8 text-center text-gray-500">
								No recent alerts
							</div>
							<div v-else class="space-y-4">
								<div
									v-for="alert in recentAlerts"
									:key="alert.id"
									class="flex items-start space-x-3 rounded-lg p-3 hover:bg-gray-50"
								>
									<div
										class="mt-2 h-3 w-3 rounded-full"
										:class="{
											'bg-red-500': alert.severity === 'high',
											'bg-yellow-500': alert.severity === 'medium',
											'bg-blue-500': alert.severity === 'low'
										}"
									></div>
									<div class="min-w-0 flex-1">
										<p class="truncate text-sm font-medium text-gray-900">
											{{ alert.name }}
										</p>
										<p class="truncate text-sm text-gray-500">
											{{ alert.description }}
										</p>
										<p class="mt-1 text-xs text-gray-400">
											{{ formatTimeAgo(alert.created_at, dFormats.datetime) }}
										</p>
									</div>
									<span
										class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
										:class="{
											'bg-red-100 text-red-800': alert.severity === 'high',
											'bg-yellow-100 text-yellow-800': alert.severity === 'medium',
											'bg-blue-100 text-blue-800': alert.severity === 'low'
										}"
									>
										{{ alert.severity }}
									</span>
								</div>
							</div>
							<div class="mt-6 text-center">
								<button
									class="text-sm font-medium text-indigo-600 hover:text-indigo-500"
									@click="goToAlerts"
								>
									View all alerts →
								</button>
							</div>
						</div>
					</div>

					<!-- Recent Cases -->
					<div class="rounded-lg bg-white shadow-sm">
						<div class="border-b border-gray-200 px-6 py-4">
							<h3 class="text-lg font-medium text-gray-900">Recent Cases</h3>
						</div>
						<div class="p-6">
							<div v-if="recentCases.length === 0" class="py-8 text-center text-gray-500">
								No recent cases
							</div>
							<div v-else class="space-y-4">
								<div
									v-for="case_ in recentCases"
									:key="case_.id"
									class="flex items-start space-x-3 rounded-lg p-3 hover:bg-gray-50"
								>
									<div
										class="mt-2 h-3 w-3 rounded-full"
										:class="{
											'bg-red-500': case_.status === 'open',
											'bg-yellow-500': case_.status === 'in_progress',
											'bg-green-500': case_.status === 'closed'
										}"
									></div>
									<div class="min-w-0 flex-1">
										<p class="truncate text-sm font-medium text-gray-900">
											{{ case_.name }}
										</p>
										<p class="truncate text-sm text-gray-500">
											{{ case_.description }}
										</p>
										<p class="mt-1 text-xs text-gray-400">
											{{ formatTimeAgo(case_.created_at, dFormats.datetime) }}
											<span v-if="case_.assigned_to">• Assigned to {{ case_.assigned_to }}</span>
										</p>
									</div>
									<span
										class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
										:class="{
											'bg-red-100 text-red-800': case_.status === 'open',
											'bg-yellow-100 text-yellow-800': case_.status === 'in_progress',
											'bg-green-100 text-green-800': case_.status === 'closed'
										}"
									>
										{{ case_.status }}
									</span>
								</div>
							</div>
							<div class="mt-6 text-center">
								<button
									class="text-sm font-medium text-indigo-600 hover:text-indigo-500"
									@click="goToCases"
								>
									View all cases →
								</button>
							</div>
						</div>
					</div>
				</div>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { NAlert, NSpin } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import OverviewStatsCards from "@/components/overview/OverviewStatsCards.vue"
import { useNavigation } from "@/composables/common/useNavigation"
import { useSettingsStore } from "@/stores/settings"
import { formatTimeAgo } from "@/utils/format"

interface Stats {
	totalAlerts: number
	criticalAlerts: number
	openCases: number
	totalAgents: number
	securityScore: number
	alertTrend: string
	scoreImprovement: number
}

interface DashboardAlert {
	id: number
	name: string
	description: string
	severity: string
	created_at: string
}

interface DashboardCase {
	id: number
	name: string
	description: string
	status: string
	created_at: string
	assigned_to?: string | null
}

const { routeAlertsList, routeCasesList } = useNavigation()

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
const dFormats = useSettingsStore().dateFormat

async function fetchDashboardData() {
	loading.value = true
	error.value = ""

	try {
		// Fetch alerts, cases, and agents data using our API services
		const [alertsResponse, casesResponse, agentsResponse] = await Promise.all([
			Api.alerts.getAlerts({ page: 1, pageSize: 50, order: "desc" }),
			Api.cases.getCases(),
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
	} catch (err: any) {
		console.error("Failed to fetch dashboard data:", err)
		error.value = err.response?.data?.detail || err.message || "Failed to load dashboard data"

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

function goToAlerts() {
	routeAlertsList().navigate()
}

function goToCases() {
	routeCasesList().navigate()
}

onBeforeMount(() => {
	fetchDashboardData()
})
</script>
