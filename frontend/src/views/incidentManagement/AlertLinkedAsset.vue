<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack">
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
import { computed, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import AlertAssetOverview from "@/components/incidentManagement/alerts/AlertAssetOverview.vue"
import { useNavigation } from "@/composables/useNavigation"

const route = useRoute()
const router = useRouter()
const { routeIncidentManagementAlerts } = useNavigation()

const BackIcon = "carbon:arrow-left"
const asset = ref<AlertAsset | null>(null)

const alertId = computed(() => {
	const raw = route.params.alertId
	const value = Array.isArray(raw) ? raw[0] : raw
	const parsed = Number.parseInt(value, 10)
	return Number.isFinite(parsed) ? parsed : null
})

const assetId = computed(() => {
	const raw = route.params.assetId
	const value = Array.isArray(raw) ? raw[0] : raw
	const parsed = Number.parseInt(value, 10)
	return Number.isFinite(parsed) ? parsed : null
})

watch([alertId, assetId], () => {
	asset.value = null
})

function goBack() {
	if (window.history.length > 1) {
		router.back()
		return
	}

	if (alertId.value != null) {
		routeIncidentManagementAlerts(alertId.value).navigate()
		return
	}

	routeIncidentManagementAlerts().navigate()
}
</script>
