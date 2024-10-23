<template>
	<n-spin :show="loading">
		<div class="header flex items-center justify-end gap-2">
			<div class="info flex grow gap-5">
				<div class="box">
					Total:
					<code>{{ flowList.length }}</code>
				</div>
			</div>
		</div>
		<div class="list my-3 flex flex-col gap-2">
			<template v-if="flowList.length">
				<AgentFlowItem
					v-for="item of flowList"
					:key="item.id"
					:flow="item"
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
import type { Agent } from "@/types/agents.d"
import type { FlowResult } from "@/types/flow.d"
import Api from "@/api"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { nanoid } from "nanoid"
import { onBeforeMount, ref, toRefs } from "vue"
import AgentFlowItem from "./AgentFlowItem.vue"

interface FlowResultExt extends FlowResult {
	id?: string
}

const props = defineProps<{
	agent: Agent
}>()
const { agent } = toRefs(props)

const message = useMessage()
const loading = ref(false)
const flowList = ref<FlowResultExt[]>([])

function getData() {
	loading.value = true

	Api.flow
		.getAllByAgent(agent.value.hostname)
		.then(res => {
			if (res.data.success) {
				flowList.value = ((res.data.results as FlowResultExt[]) || []).map(o => {
					o.id = nanoid()
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
			flowList.value = flow_results
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

<style lang="scss" scoped>
.list {
	container-type: inline-size;
	min-height: 200px;
}
</style>
