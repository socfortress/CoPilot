<template>
	<div class="flex flex-col gap-2">
		<template v-if="assets.length">
			<AlertAssetItem :asset embedded v-for="asset of assets" :key="asset.id" />
		</template>
		<template v-else>
			<n-empty description="No assets found" class="justify-center h-48" />
		</template>
	</div>
</template>

<script setup lang="ts">
import { toRefs } from "vue"
import { NEmpty } from "naive-ui"
import AlertAssetItem from "./AlertAsset.vue"
import type { AlertAsset } from "@/types/incidentManagement/alerts.d"

const props = defineProps<{ assets: AlertAsset[] }>()
const { assets } = toRefs(props)
</script>
