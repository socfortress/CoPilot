<template>
	<div class="soc-assets-list">
		<n-spin :show="loadingAssets" class="min-h-14">
			<div class="flex flex-col gap-2 px-7 py-4 pb-0">
				<div v-if="assetsState" class="box">
					State:
					<code>{{ assetsState.object_state }}</code>
				</div>
				<div v-if="assetsState" class="box">
					Last update:
					<code>{{ formatDateTime(assetsState.object_last_update) }}</code>
				</div>
			</div>
			<div v-if="assetsList?.length" class="flex flex-col gap-2 p-7">
				<SocCaseAssetsItem v-for="asset of assetsList" :key="asset.asset_id" :asset="asset" />
			</div>
			<template v-else>
				<n-empty v-if="!loadingAssets" description="No items found" class="h-48 justify-center" />
			</template>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { SocCaseAsset, SocCaseAssetsState } from "@/types/soc/asset.d"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import SocCaseAssetsItem from "./SocCaseAssetsItem.vue"

const { caseId } = defineProps<{ caseId: string | number }>()

const loadingAssets = ref(false)
const message = useMessage()

const assetsList = ref<SocCaseAsset[] | null>(null)
const assetsState = ref<SocCaseAssetsState | null>(null)

const dFormats = useSettingsStore().dateFormat

function formatDateTime(timestamp: string | number | Date, utc: boolean = true): string {
	return dayjs(timestamp).utc(utc).format(dFormats.datetimesec)
}

function getAssets() {
	loadingAssets.value = true

	Api.soc
		.getAssetsByCase(caseId.toString())
		.then(res => {
			if (res.data.success) {
				assetsList.value = res.data?.assets || null
				assetsState.value = res.data?.state || null
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
