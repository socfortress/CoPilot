<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button
				quaternary
				class="shrink-0"
				@click="goBack(routeIncidentManagementAlertAsset(alertId ?? undefined))"
			>
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<div v-if="asset" class="flex min-w-0 flex-wrap items-baseline gap-2">
				<span class="truncate text-lg font-semibold">{{ asset.asset_name }}</span>
				<span class="text-secondary font-mono text-sm">#{{ asset.id }}</span>
			</div>
		</div>

		<AlertAssetOverview
			v-if="alertId != null && assetId != null"
			:key="`${alertId}-${assetId}`"
			:alert-id
			:asset-id
			full-width
			@loaded="asset = $event"
		/>
		<n-empty v-else description="Invalid asset ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { AlertAsset } from "@/types/incidentManagement/alerts"
import { NButton, NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import AlertAssetOverview from "@/components/incidentManagement/alerts/AlertAssetOverview.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { goBack, routeIncidentManagementAlertAsset } = useNavigation()

const BackIcon = "carbon:arrow-left"
const asset = ref<AlertAsset | null>(null)

const alertId = useRouteIdParam("alertId")
const assetId = useRouteIdParam("assetId")

watch([alertId, assetId], () => {
	asset.value = null
})
</script>
