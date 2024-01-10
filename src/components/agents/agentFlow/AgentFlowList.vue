<template>
	<n-spin :show="loading">
		<div class="header flex items-center justify-end gap-2">
			<div class="info grow flex gap-5">
				<div class="box">
					Total:
					<code>{{ flowList.length }}</code>
				</div>
			</div>
		</div>
		<div class="list my-3">
			<template v-if="flowList.length">
				<AgentFlowItem v-for="item of flowList" :key="item.session_id" :flow="item" class="mb-2" />
			</template>
			<template v-else>
				<n-empty description="No items found" class="justify-center h-48" v-if="!loading" />
			</template>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, toRefs } from "vue"
import { useMessage, NSpin, NEmpty } from "naive-ui"
import AgentFlowItem from "./AgentFlowItem.vue"
import Api from "@/api"
import type { Agent } from "@/types/agents.d"
import type { FlowResult } from "@/types/flow.d"

const props = defineProps<{
	agent: Agent
}>()
const { agent } = toRefs(props)

const message = useMessage()
const loading = ref(false)
const flowList = ref<FlowResult[]>([])

function getData() {
	loading.value = true

	Api.flow
		.getAllByAgent(agent.value.hostname)
		.then(res => {
			if (res.data.success) {
				flowList.value = res.data.results || []
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
