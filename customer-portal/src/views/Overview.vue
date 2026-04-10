<template>
	<div class="page md:page-wrapped flex flex-col gap-6 md:overflow-hidden">
		<p>Monitor your organization's security posture and recent activity</p>

		<div class="flex grow flex-col gap-6 overflow-hidden">
			<div class="@container flex grow flex-col gap-6 overflow-hidden">
				<OverviewStatsCards />

				<n-spin
					:show="loading"
					class="overflow-hidden"
					content-class="flex max-h-full grow flex-col overflow-hidden"
				>
					<div class="flex grow flex-col gap-6 overflow-hidden @2xl:flex-row">
						<div class="max-h-full basis-1/2 overflow-hidden">
							<OverviewRecentAlerts :recent-alerts class="h-full" size="small" />
						</div>
						<div class="max-h-full basis-1/2 overflow-hidden">
							<OverviewRecentCases :recent-cases class="h-full" size="small" />
						</div>
					</div>
				</n-spin>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { DashboardAlert, DashboardCase } from "@/components/overview/types"
import type { ApiError } from "@/types/common"
import { NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import OverviewRecentAlerts from "@/components/overview/OverviewRecentAlerts.vue"
import OverviewRecentCases from "@/components/overview/OverviewRecentCases.vue"
import OverviewStatsCards from "@/components/overview/OverviewStatsCards.vue"
import { getApiErrorMessage } from "@/utils"

const loading = ref(true)
const message = useMessage()
const recentAlerts = ref<DashboardAlert[]>([])
const recentCases = ref<DashboardCase[]>([])

async function fetchDashboardData() {
	loading.value = true

	try {
		// Fetch alerts, cases, and agents data using our API services
		const [alertsResponse, casesResponse] = await Promise.all([
			Api.alerts.getAlerts({ page: 1, pageSize: 10, order: "desc" }),
			Api.cases.getCases({ page: 1, pageSize: 10, order: "desc" })
		])

		const alerts = alertsResponse.data.alerts || []
		const cases = casesResponse.data.cases || []

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
			.slice(0, 10)

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
			.slice(0, 10)
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		loading.value = false
	}
}

onBeforeMount(() => {
	fetchDashboardData()
})
</script>
