<template>
	<n-spin :show="loading">
		<div class="header flex items-center justify-end gap-2">
			<div class="info flex grow gap-5">
				<div class="box">
					Total:
					<code>{{ collectList.length }}</code>
				</div>
			</div>
		</div>
		<div class="my-3 flex min-h-52 flex-col gap-4">
			<template v-if="collectList.length">
				<CollectItem
					v-for="item of collectList"
					:key="item.___id"
					:collect="item"
					embedded
					class="item-appear item-appear-bottom item-appear-005"
				/>
			</template>
			<template v-else>
				<n-empty v-if="!loading" description="No items found" class="h-48 justify-center" />
			</template>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { CollectResult, FlowResult } from "@/types/flow.d"
import Api from "@/api"
import CollectItem from "@/components/artifacts/CollectItem.vue"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { nanoid } from "nanoid"
import { onBeforeMount, ref } from "vue"

const { flow } = defineProps<{
	flow: FlowResult
}>()

const message = useMessage()
const loading = ref(false)
const collectList = ref<CollectResult[]>([])

function getData() {
	loading.value = true

	Api.flow
		.retrieve(flow.client_id, flow.session_id)
		.then(res => {
			if (res.data.success) {
				collectList.value = (res.data.results || []).map(o => {
					o.___id = nanoid()
					return o
				})
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			// MOCK
			/*
			collectList.value = collect_result
			*/
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	getData()
})
</script>
