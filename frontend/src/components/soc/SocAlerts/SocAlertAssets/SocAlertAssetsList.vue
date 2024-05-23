<template>
	<div class="soc-assets-list">
		<n-spin :show="loadingAssets" style="min-height: 50px">
			<div v-if="assetsList?.length" class="p-7 flex flex-col gap-2">
				<SocAlertAssetsItem v-for="asset of assetsList" :key="asset.asset_id" :asset="asset" />
			</div>
			<template v-else>
				<n-empty description="No items found" class="justify-center h-48" v-if="!loadingAssets" />
			</template>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { ref } from "vue"
import SocAlertAssetsItem from "./SocAlertAssetsItem.vue"
import Api from "@/api"
import { useMessage, NSpin, NEmpty } from "naive-ui"
import type { SocAlertAsset } from "@/types/soc/asset.d"
import { onBeforeMount } from "vue"

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
