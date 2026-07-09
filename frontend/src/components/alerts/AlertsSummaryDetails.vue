<template>
	<n-spin :show="loading">
		<AlertsSummaryItem
			v-if="alertsSummary"
			:alerts-summary
			hide-open
			initial-expanded
		/>
		<n-empty v-else-if="!loading" description="No alerts summary found" class="h-48 justify-center" />
	</n-spin>
</template>

<script setup lang="ts">
import type { AlertsSummaryExt } from "./AlertsSummary.vue"
import type { GraylogIndexAlertsQuery } from "@/api/endpoints/alerts"
import type { ApiError } from "@/types/common"
import axios from "axios"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, onBeforeUnmount, ref, toRefs } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
import AlertsSummaryItem from "./AlertsSummary.vue"

const props = defineProps<{
	indexName: string
	query?: Partial<GraylogIndexAlertsQuery>
}>()

const { indexName, query } = toRefs(props)

const message = useMessage()
const loading = ref(false)
const alertsSummary = ref<AlertsSummaryExt | null>(null)
let abortController: AbortController | null = null

function load() {
	abortController?.abort()
	abortController = new AbortController()
	loading.value = true

	Api.alerts
		.getGraylogAlertsSummary(
			{
				index_name: indexName.value,
				size: query.value?.size ?? 10,
				timerange: query.value?.timerange ?? "24h",
				index_prefix: query.value?.index_prefix ?? "gl-events*"
			},
			abortController.signal
		)
		.then(res => {
			alertsSummary.value = res.data?.alerts_summary?.[0] ?? null
			if (!res.data.success && !alertsSummary.value) {
				message.warning(res.data?.message || "No alerts summary found")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				alertsSummary.value = null
				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	load()
})

onBeforeUnmount(() => {
	abortController?.abort()
})

defineExpose({ reload: load })
</script>
