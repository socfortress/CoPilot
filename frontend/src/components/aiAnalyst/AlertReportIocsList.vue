<template>
	<n-spin :show="loading" class="min-h-40">
		<div class="flex flex-col gap-2">
			<template v-if="iocs.length">
				<IocItem v-for="ioc of iocs" :key="ioc.id" :ioc />
			</template>
			<n-empty v-else-if="!loading" description="No IOCs found for this alert" class="min-h-40 justify-center" />
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { AiAnalystIoc } from "@/types/ai-analyst"
import type { ApiError } from "@/types/common"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref, toRefs } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
import IocItem from "./IocItem.vue"

const props = defineProps<{
	alertId: number
}>()

const { alertId } = toRefs(props)

const message = useMessage()
const loading = ref(false)
const iocs = ref<AiAnalystIoc[]>([])

function getData() {
	loading.value = true

	Api.aiAnalyst
		.getIocsByAlert(alertId.value)
		.then(res => {
			if (res.data.success) {
				iocs.value = res.data?.iocs || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	getData()
})
</script>
