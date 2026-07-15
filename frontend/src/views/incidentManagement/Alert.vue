<template>
	<div class="page flex flex-col gap-4 pb-0!">
		<DetailPageHeader :title="alert?.alert_name" :back-route="routeIncidentManagementAlerts()">
			<template v-if="alert" #meta>
				<span class="text-secondary font-mono text-sm">#{{ alert.id }}</span>
				<span class="text-secondary text-sm">{{ alert.source }}</span>
			</template>
		</DetailPageHeader>

		<AlertDetails
			v-if="alertId"
			:key="alertId"
			:alert-id
			class="grow"
			full-width
			@loaded="alert = $event"
			@updated="alert = $event"
			@deleted="routeIncidentManagementAlerts().navigate()"
		/>
		<n-empty v-else description="Invalid alert ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { Alert } from "@/types/incidentManagement/alerts"
import { NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import AlertDetails from "@/components/incidentManagement/alerts/AlertDetails.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { routeIncidentManagementAlerts } = useNavigation()

const alert = ref<Alert | null>(null)

const alertId = useRouteIdParam("id")

watch(alertId, () => {
	alert.value = null
})
</script>
