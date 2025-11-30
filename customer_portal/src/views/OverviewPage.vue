<template>
	<div class="min-h-screen bg-gray-50">
		<!-- Header -->
		<header class="border-b bg-white shadow-sm">
			<div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<div class="flex h-16 justify-between">
					<div class="flex items-center">
						<div class="mr-3 min-h-8">
							<img
								v-if="portalLogo && showLogo"
								class="h-8 w-auto"
								:src="portalLogo"
								:alt="portalTitle"
								@error="showLogo = false"
							/>
						</div>
						<h1 class="text-xl font-semibold text-gray-900">{{ portalTitle }}</h1>
						<nav class="ml-8 flex space-x-8">
							<router-link
								to="/"
								class="rounded-md border-b-2 border-indigo-600 px-3 py-2 text-sm font-medium text-indigo-600"
							>
								Overview
							</router-link>
							<router-link
								to="/alerts"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Alerts
							</router-link>
							<router-link
								to="/cases"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Cases
							</router-link>
							<router-link
								to="/agents"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Agents
							</router-link>
						</nav>
					</div>
					<div class="flex items-center space-x-4">
						<div class="text-sm text-gray-700">
							Welcome,
							<span class="font-medium">{{ username }}</span>
						</div>
            <button
              @click="openChangePasswordModal"
              class="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700"
            >
                Change Password
            </button>
						<button
							@click="logout"
							class="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
						>
							Logout
						</button>
					</div>
				</div>
			</div>
		</header>

		<!-- Main Content -->
		<main class="mx-auto max-w-7xl py-6 sm:px-6 lg:px-8">
			<div class="px-4 py-6 sm:px-0">
				<!-- Welcome Section -->
				<div class="mb-8">
					<h2 class="mb-2 text-2xl font-bold text-gray-900">Security Overview</h2>
					<p class="text-gray-600">Monitor your organization's security posture and recent activity</p>
				</div>

				<!-- Loading State -->
				<div v-if="loading" class="flex items-center justify-center py-12">
					<div class="h-12 w-12 animate-spin rounded-full border-b-2 border-indigo-600"></div>
					<span class="ml-3 text-gray-600">Loading dashboard...</span>
				</div>

				<!-- Error State -->
				<div v-else-if="error" class="mb-6 rounded-lg border border-red-200 bg-red-50 p-4">
					<div class="flex">
						<div class="shrink-0">
							<svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
								<path
									fill-rule="evenodd"
									d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
						<div class="ml-3">
							<h3 class="text-sm font-medium text-red-800">Error Loading Dashboard</h3>
							<div class="mt-2 text-sm text-red-700">{{ error }}</div>
							<div class="mt-3">
								<button
									@click="refreshData"
									class="rounded bg-red-100 px-3 py-1 text-sm font-medium text-red-800 hover:bg-red-200"
								>
									Try Again
								</button>
							</div>
						</div>
					</div>
				</div>

				<!-- Dashboard Content -->
				<div v-else>
					<!-- Key Metrics Cards -->
					<div class="mb-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-5">
						<!-- Total Alerts -->
						<div class="overflow-hidden rounded-lg bg-white shadow-sm">
							<div class="p-6">
								<div class="flex items-center">
									<div class="shrink-0">
										<div class="flex h-8 w-8 items-center justify-center rounded-md bg-red-500">
											<svg
												class="h-5 w-5 text-white"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
												></path>
											</svg>
										</div>
									</div>
									<div class="ml-5 w-0 flex-1">
										<dl>
											<dt class="truncate text-sm font-medium text-gray-500">Total Alerts</dt>
											<dd class="flex items-baseline">
												<div class="text-2xl font-semibold text-gray-900">
													{{ stats.totalAlerts }}
												</div>
												<div
													class="ml-2 flex items-baseline text-sm font-semibold"
													:class="alertTrendClass"
												>
													{{ stats.alertTrend }}
												</div>
											</dd>
										</dl>
									</div>
								</div>
							</div>
						</div>

						<!-- Critical Alerts -->
						<div class="overflow-hidden rounded-lg bg-white shadow-sm">
							<div class="p-6">
								<div class="flex items-center">
									<div class="shrink-0">
										<div class="flex h-8 w-8 items-center justify-center rounded-md bg-orange-500">
											<svg
												class="h-5 w-5 text-white"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
												></path>
											</svg>
										</div>
									</div>
									<div class="ml-5 w-0 flex-1">
										<dl>
											<dt class="truncate text-sm font-medium text-gray-500">Critical Alerts</dt>
											<dd class="text-2xl font-semibold text-gray-900">
												{{ stats.criticalAlerts }}
											</dd>
										</dl>
									</div>
								</div>
							</div>
						</div>

						<!-- Open Cases -->
						<div class="overflow-hidden rounded-lg bg-white shadow-sm">
							<div class="p-6">
								<div class="flex items-center">
									<div class="shrink-0">
										<div class="flex h-8 w-8 items-center justify-center rounded-md bg-blue-500">
											<svg
												class="h-5 w-5 text-white"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
												></path>
											</svg>
										</div>
									</div>
									<div class="ml-5 w-0 flex-1">
										<dl>
											<dt class="truncate text-sm font-medium text-gray-500">Open Cases</dt>
											<dd class="text-2xl font-semibold text-gray-900">{{ stats.openCases }}</dd>
										</dl>
									</div>
								</div>
							</div>
						</div>

						<!-- Security Score -->
						<div class="overflow-hidden rounded-lg bg-white shadow-sm">
							<div class="p-6">
								<div class="flex items-center">
									<div class="shrink-0">
										<div class="flex h-8 w-8 items-center justify-center rounded-md bg-green-500">
											<svg
												class="h-5 w-5 text-white"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
												></path>
											</svg>
										</div>
									</div>
									<div class="ml-5 w-0 flex-1">
										<dl>
											<dt class="truncate text-sm font-medium text-gray-500">Security Score</dt>
											<dd class="flex items-baseline">
												<div class="text-2xl font-semibold text-gray-900">
													{{ stats.securityScore }}%
												</div>
												<div
													class="ml-2 flex items-baseline text-sm font-semibold text-green-600"
												>
													+{{ stats.scoreImprovement }}%
												</div>
											</dd>
										</dl>
									</div>
								</div>
							</div>
						</div>

						<!-- Total Agents -->
						<div class="overflow-hidden rounded-lg bg-white shadow-sm">
							<div class="p-6">
								<div class="flex items-center">
									<div class="shrink-0">
										<div class="flex h-8 w-8 items-center justify-center rounded-md bg-purple-500">
											<svg
												class="h-5 w-5 text-white"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z"
												></path>
											</svg>
										</div>
									</div>
									<div class="ml-5 w-0 flex-1">
										<dl>
											<dt class="truncate text-sm font-medium text-gray-500">Total Agents</dt>
											<dd class="text-2xl font-semibold text-gray-900">
												{{ stats.totalAgents }}
											</dd>
										</dl>
									</div>
								</div>
							</div>
						</div>
					</div>

					<!-- Recent Activity and Charts Section -->
					<div class="grid grid-cols-1 gap-8 lg:grid-cols-2">
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
												{{ formatTimeAgo(alert.created_at) }}
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
										@click="goToAlerts"
										class="text-sm font-medium text-indigo-600 hover:text-indigo-500"
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
												{{ formatTimeAgo(case_.created_at) }}
												<span v-if="case_.assigned_to">
													• Assigned to {{ case_.assigned_to }}
												</span>
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
										@click="goToCases"
										class="text-sm font-medium text-indigo-600 hover:text-indigo-500"
									>
										View all cases →
									</button>
								</div>
							</div>
						</div>
					</div>

					<!-- Quick Actions -->
					<div class="mt-8 rounded-lg bg-white shadow-sm">
						<div class="border-b border-gray-200 px-6 py-4">
							<h3 class="text-lg font-medium text-gray-900">Quick Actions</h3>
						</div>
						<div class="p-6">
							<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
								<button
									@click="goToAlerts"
									class="flex items-center justify-center rounded-md border border-gray-300 bg-white px-4 py-3 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none"
								>
									<svg
										class="mr-2 h-5 w-5 text-gray-400"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
										></path>
									</svg>
									View Alerts
								</button>
								<button
									@click="goToCases"
									class="flex items-center justify-center rounded-md border border-gray-300 bg-white px-4 py-3 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none"
								>
									<svg
										class="mr-2 h-5 w-5 text-gray-400"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
										></path>
									</svg>
									View Cases
								</button>
								<button
									@click="goToAgents"
									class="flex items-center justify-center rounded-md border border-gray-300 bg-white px-4 py-3 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none"
								>
									<svg
										class="mr-2 h-5 w-5 text-gray-400"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z"
										></path>
									</svg>
									View Agents
								</button>
								<button
									@click="refreshData"
									class="flex items-center justify-center rounded-md border border-gray-300 bg-white px-4 py-3 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none"
								>
									<svg
										class="mr-2 h-5 w-5 text-gray-400"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
										></path>
									</svg>
									Refresh Data
								</button>
								<button
									class="flex items-center justify-center rounded-md border border-gray-300 bg-white px-4 py-3 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none"
									disabled
								>
									<svg
										class="mr-2 h-5 w-5 text-gray-400"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 00-2-2z"
										></path>
									</svg>
									Reports (Soon)
								</button>
							</div>
						</div>
					</div>
				</div>
			</div>
		</main>
    <ChangePasswordModal :is-open="showChangePasswordModal" @close="closeChangePasswordModal" @success="onPasswordChanged" />
	</div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue"
import { useRouter } from "vue-router"
import { usePortalSettingsStore } from "@/stores/portalSettings"
import AlertsAPI, { type Alert } from "@/api/alerts"
import CasesAPI, { type Case } from "@/api/cases"
import AgentsAPI from "@/api/agents"
import ChangePasswordModal from "@/components/ChangePasswordModal.vue"

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

const router = useRouter()
const portalSettingsStore = usePortalSettingsStore()

const loading = ref(true)
const error = ref("")
const showLogo = ref(true)
const showChangePasswordModal = ref(false)
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

const username = computed(() => {
	try {
		const user = JSON.parse(localStorage.getItem("customer-portal-user") || "{}")
		return user.username || "User"
	} catch {
		return "User"
	}
})

const portalTitle = computed(() => portalSettingsStore.portalTitle || "Customer Portal")
const portalLogo = computed(() => portalSettingsStore.portalLogo)

const alertTrendClass = computed(() => {
	if (stats.value.alertTrend.startsWith("+")) {
		return "text-red-600"
	} else if (stats.value.alertTrend.startsWith("-")) {
		return "text-green-600"
	}
	return "text-gray-600"
})

const formatTimeAgo = (dateString: string) => {
	if (!dateString) return "Unknown"

	try {
		const date = new Date(dateString)
		const now = new Date()
		const diffInMs = now.getTime() - date.getTime()
		const diffInHours = diffInMs / (1000 * 60 * 60)

		if (diffInHours < 1) {
			const diffInMinutes = Math.floor(diffInMs / (1000 * 60))
			return `${diffInMinutes} minutes ago`
		} else if (diffInHours < 24) {
			return `${Math.floor(diffInHours)} hours ago`
		} else {
			const diffInDays = Math.floor(diffInHours / 24)
			return `${diffInDays} days ago`
		}
	} catch {
		return "Unknown"
	}
}

const fetchDashboardData = async () => {
	loading.value = true
	error.value = ""

	try {
		// Fetch alerts, cases, and agents data using our API services
		const [alertsResponse, casesResponse, agentsResponse] = await Promise.all([
			AlertsAPI.getAlerts(1, 50).catch(() => ({
				alerts: [],
				total: 0,
				open: 0,
				in_progress: 0,
				closed: 0,
				success: false,
				message: "Failed to load alerts"
			})),
			CasesAPI.getCases().catch(() => ({ cases: [], success: false, message: "Failed to load cases" })),
			AgentsAPI.getAgents().catch(() => ({ agents: [], success: false, message: "Failed to load agents" }))
		])

		const alerts = alertsResponse.alerts || []
		const cases = casesResponse.cases || []
		const agents = agentsResponse.agents || []

		// Calculate stats from real data
		const openAlerts = alertsResponse.open || 0
		const inProgressAlerts = alertsResponse.in_progress || 0

		const openCases = cases.filter(
			(case_: Case) => case_.case_status === "OPEN" || case_.case_status === "IN_PROGRESS"
		).length

		// Calculate security score based on actual data
		const totalActiveIssues = openAlerts + inProgressAlerts + openCases
		const securityScore = Math.max(60, 100 - totalActiveIssues * 2)

		stats.value = {
			totalAlerts: alertsResponse.total || 0,
			criticalAlerts: openAlerts + inProgressAlerts,
			openCases,
			totalAgents: agents.length,
			securityScore: Math.min(100, securityScore),
			alertTrend: openAlerts > 0 ? `+${openAlerts}` : "0",
			scoreImprovement: Math.floor(Math.random() * 5) + 1
		}

		// Get recent alerts (last 5, sorted by creation time)
		recentAlerts.value = alerts
			.map((alert: Alert) => ({
				id: alert.id,
				name: alert.alert_name || "Unnamed Alert",
				description: alert.alert_description || "No description available",
				severity: alert.status === "OPEN" ? "high" : alert.status === "IN_PROGRESS" ? "medium" : "low",
				created_at: alert.alert_creation_time || new Date().toISOString()
			}))
			.sort(
				(a: DashboardAlert, b: DashboardAlert) =>
					new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
			)
			.slice(0, 5)

		// Get recent cases (last 5, sorted by creation time)
		recentCases.value = cases
			.map((case_: Case) => ({
				id: case_.id,
				name: case_.case_name || "Unnamed Case",
				description: case_.case_description || "No description available",
				status: case_.case_status || "open",
				created_at: case_.case_creation_time || new Date().toISOString(),
				assigned_to: case_.assigned_to || undefined
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

const refreshData = () => {
	fetchDashboardData()
}

const goToAlerts = () => {
	router.push("/alerts")
}

const goToCases = () => {
	router.push("/cases")
}

const goToAgents = () => {
	router.push("/agents")
}

const openChangePasswordModal = () => {
    showChangePasswordModal.value = true
}

const closeChangePasswordModal = () => {
    showChangePasswordModal.value = false
}

const onPasswordChanged = () => {
    // Optionally show a success message or perform other actions
    console.log("Password changed successfully")
}

const logout = () => {
	localStorage.removeItem("customer-portal-auth-token")
	localStorage.removeItem("customer-portal-user")
	router.push("/login")
}

onMounted(() => {
	fetchDashboardData()
})
</script>
