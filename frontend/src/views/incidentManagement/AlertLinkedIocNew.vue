<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack(routeIncidentManagementAlerts(alertId ?? undefined))">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<div class="flex min-w-0 flex-wrap items-baseline gap-2">
				<span class="truncate text-lg font-semibold">Create IoC</span>
				<span v-if="alertId != null" class="text-secondary font-mono text-sm">Alert #{{ alertId }}</span>
			</div>
		</div>

		<AlertIoCsForm v-if="alertId != null" :alert-id @submitted="onSubmitted($event)" />
		<n-empty v-else description="Invalid alert ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { AlertIOC } from "@/types/incidentManagement/alerts"
import { NButton, NEmpty } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import AlertIoCsForm from "@/components/incidentManagement/alerts/AlertIoCsForm.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { goBack, routeIncidentManagementAlerts, routeIncidentManagementAlertIoc } = useNavigation()

const BackIcon = "carbon:arrow-left"

const alertId = useRouteIdParam("alertId")

function onSubmitted(ioc: AlertIOC) {
	// land on the IoC we just created rather than back on an empty form
	routeIncidentManagementAlertIoc(alertId.value ?? undefined, ioc.id).replace()
}
</script>
