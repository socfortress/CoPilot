<template>
	<div class="flex flex-col gap-2">
		<template v-if="assets.length">
			<AlertAssetItem v-for="asset of assets" :key="asset.id" :asset embedded />
		</template>
		<template v-else>
			<n-empty description="No assets found" class="justify-center h-48" />
		</template>
	</div>
</template>

<script setup lang="ts">
import type { AlertAsset } from "@/types/incidentManagement/alerts.d"
import { NEmpty } from "naive-ui"
import { toRefs } from "vue"
import AlertAssetItem from "./AlertAsset.vue"

const props = defineProps<{ assets: AlertAsset[] }>()
const { assets } = toRefs(props)
</script>
