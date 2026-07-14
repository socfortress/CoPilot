<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack(routeIncidentManagementAlerts(alertId ?? undefined))">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<div v-if="ioc" class="flex min-w-0 flex-wrap items-baseline gap-2">
				<span class="truncate font-mono text-lg font-semibold">{{ ioc.value }}</span>
				<span class="text-secondary font-mono text-sm">#{{ ioc.id }}</span>
				<span class="text-secondary text-sm">{{ ioc.type }}</span>
			</div>
		</div>

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
import { NButton, NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import AlertIoCOverview from "@/components/incidentManagement/alerts/AlertIoCOverview.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { goBack, routeIncidentManagementAlerts } = useNavigation()

const BackIcon = "carbon:arrow-left"
const ioc = ref<AlertIOC | null>(null)

const alertId = useRouteIdParam("alertId")
const iocId = useRouteIdParam("iocId")

watch([alertId, iocId], () => {
	ioc.value = null
})
</script>
