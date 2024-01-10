<template>
	<n-spin :show="loading">
		<div class="header flex items-center justify-end gap-2">
			<div class="info grow flex gap-5">
				<div class="box">
					Total:
					<code>{{ collectList.length }}</code>
				</div>
			</div>
		</div>
		<div class="list my-3">
			<template v-if="collectList.length">
				<AgentFlowCollectItem
					v-for="item of collectList"
					:key="item.id"
					:collect="item"
					embedded
					class="mb-2 item-appear item-appear-bottom item-appear-005"
				/>
			</template>
			<template v-else>
				<n-empty description="No items found" class="justify-center h-48" v-if="!loading" />
			</template>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import { ref, onBeforeMount } from "vue"
import { useMessage, NSpin, NEmpty } from "naive-ui"
import AgentFlowCollectItem from "./AgentFlowCollectItem.vue"
import Api from "@/api"
import type { CollectResult, FlowResult } from "@/types/flow.d"
import { nanoid } from "nanoid"

interface CollectResultExt extends CollectResult {
	id?: string
}

const { flow } = defineProps<{
	flow: FlowResult
}>()

const message = useMessage()
const loading = ref(false)
const collectList = ref<CollectResultExt[]>([])

function getData() {
	loading.value = true

	Api.flow
		.retrieve(flow.client_id, flow.session_id)
		.then(res => {
			if (res.data.success) {
				collectList.value = ((res.data.results as CollectResultExt[]) || []).map(o => {
					o.id = nanoid()
					return o
				})
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	getData()
})
</script>

<style lang="scss" scoped>
.list {
	container-type: inline-size;
	min-height: 200px;
}
</style>
