<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader title="Create IoC" :back-route="routeIncidentManagementAlerts(alertId ?? undefined)">
			<template v-if="alertId != null" #meta>
				<span class="text-secondary font-mono text-sm">Alert #{{ alertId }}</span>
			</template>
		</DetailPageHeader>

		<AlertIoCsForm v-if="alertId != null" :alert-id @submitted="onSubmitted($event)" />
		<n-empty v-else description="Invalid alert ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { AlertIOC } from "@/types/incidentManagement/alerts"
import { NEmpty } from "naive-ui"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import AlertIoCsForm from "@/components/incidentManagement/alerts/AlertIoCsForm.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { routeIncidentManagementAlerts, routeIncidentManagementAlertIoc } = useNavigation()

const alertId = useRouteIdParam("alertId")

function onSubmitted(ioc: AlertIOC) {
	// land on the IoC we just created rather than back on an empty form
	routeIncidentManagementAlertIoc(alertId.value ?? undefined, ioc.id).replace()
}
</script>
