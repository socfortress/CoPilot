<template>
	<div class="soc-assets-list">
		<n-spin :show="loadingAssets" class="min-h-14">
			<div v-if="assetsList?.length" class="flex flex-col gap-2 p-7">
				<SocAlertAssetsItem v-for="asset of assetsList" :key="asset.asset_id" :asset="asset" />
			</div>
			<template v-else>
				<n-empty v-if="!loadingAssets" description="No items found" class="h-48 justify-center" />
			</template>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { SocAlertAsset } from "@/types/soc/asset.d"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import SocAlertAssetsItem from "./SocAlertAssetsItem.vue"

const { alertId } = defineProps<{ alertId: string | number }>()

const loadingAssets = ref(false)
const message = useMessage()

const assetsList = ref<SocAlertAsset[] | null>(null)

function getAssets() {
	loadingAssets.value = true

	Api.soc
		.getAssetsByAlert(alertId.toString())
		.then(res => {
			if (res.data.success) {
				assetsList.value = res.data?.assets || null
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingAssets.value = false
		})
}

onBeforeMount(() => {
	getAssets()
})
</script>
