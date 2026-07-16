<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :back-route="routeIncidentManagementAlerts(alertId ?? undefined)">
			<template v-if="ioc" #title>
				<span class="truncate font-mono text-lg font-semibold">{{ ioc.value }}</span>
			</template>
			<template v-if="ioc" #meta>
				<span class="text-secondary font-mono text-sm">#{{ ioc.id }}</span>
				<span class="text-secondary text-sm">{{ ioc.type }}</span>
			</template>
		</DetailPageHeader>

		<AlertIoCOverview
			v-if="alertId != null && iocId != null"
			:key="`${alertId}-${iocId}`"
			:alert-id
			:ioc-id
			full-width
			@loaded="ioc = $event"
		/>
		<n-empty v-else description="Invalid IoC ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { AlertIOC } from "@/types/incidentManagement/alerts"
import { NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import AlertIoCOverview from "@/components/incidentManagement/alerts/AlertIoCOverview.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { routeIncidentManagementAlerts } = useNavigation()

const ioc = ref<AlertIOC | null>(null)

const alertId = useRouteIdParam("alertId")
const iocId = useRouteIdParam("iocId")

watch([alertId, iocId], () => {
	ioc.value = null
})
</script>
