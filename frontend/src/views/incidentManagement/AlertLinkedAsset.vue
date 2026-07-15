<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :title="asset?.asset_name" :back-route="routeIncidentManagementAlertAsset(alertId ?? undefined)">
			<template v-if="asset" #meta>
				<span class="text-secondary font-mono text-sm">#{{ asset.id }}</span>
			</template>
		</DetailPageHeader>

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
import { NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import AlertAssetOverview from "@/components/incidentManagement/alerts/AlertAssetOverview.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { routeIncidentManagementAlertAsset } = useNavigation()

const asset = ref<AlertAsset | null>(null)

const alertId = useRouteIdParam("alertId")
const assetId = useRouteIdParam("assetId")

watch([alertId, assetId], () => {
	asset.value = null
})
</script>
