<template>
	<n-spin :show="loading">
		<div class="header flex items-center justify-end gap-2">
			<div class="info grow flex gap-5">
				<div class="box">
					Total:
					<code>{{ casesList.length }}</code>
				</div>
			</div>
		</div>
		<div class="list my-3">
			<template v-if="casesList.length">
				<SocCaseItem
					v-for="item of casesList"
					:key="item"
					:caseId="item"
					@deleted="getData()"
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
import { ref, onBeforeMount, toRefs, onBeforeUnmount } from "vue"
import { useMessage, NSpin, NEmpty } from "naive-ui"
import SocCaseItem from "@/components/soc/SocCases/SocCaseItem.vue"
import Api from "@/api"
import type { Agent } from "@/types/agents.d"
import axios from "axios"

const props = defineProps<{
	agent: Agent
}>()
const { agent } = toRefs(props)

const message = useMessage()
const loading = ref(false)
const casesList = ref<number[]>([])
let abortController: AbortController | null = null

function getData() {
	loading.value = true

	abortController = new AbortController()

	Api.agents
		.getSocCases(agent.value.agent_id, abortController.signal)
		.then(res => {
			if (res.data.success) {
				casesList.value = res.data.case_ids || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	getData()
})

onBeforeUnmount(() => {
	abortController?.abort()
})
</script>

<style lang="scss" scoped>
.list {
	container-type: inline-size;
	min-height: 200px;
}
</style>
