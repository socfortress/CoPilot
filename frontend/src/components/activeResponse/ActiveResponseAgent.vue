<template>
	<div class="active-response-list">
		<n-spin :show="loadingActiveResponse">
			<div class="list">
				<template v-if="activeResponseList.length">
					<ActiveResponseItem
						v-for="activeResponse of activeResponseList"
						:key="activeResponse.name"
						:activeResponse="activeResponse"
						:embedded="embedded"
						:agent-id="agent.agent_id"
						class="item-appear item-appear-bottom item-appear-005 mb-2"
					/>
				</template>
				<template v-else>
					<n-empty description="No items found" class="justify-center h-48" v-if="!loadingActiveResponse" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount } from "vue"
import { useMessage, NSpin, NEmpty } from "naive-ui"
import Api from "@/api"
import ActiveResponseItem from "./ActiveResponseItem.vue"
import type { Agent } from "@/types/agents.d"
import type { SupportedActiveResponse } from "@/types/activeResponse.d"

const { embedded, agent } = defineProps<{
	embedded?: boolean
	agent: Agent
}>()

const message = useMessage()
const loadingActiveResponse = ref(false)
const activeResponseList = ref<SupportedActiveResponse[]>([])

function getAvailableIntegrations() {
	loadingActiveResponse.value = true

	Api.activeResponse
		.getSupported(agent.agent_id)
		.then(res => {
			if (res.data.success) {
				activeResponseList.value = res.data?.supported_active_responses || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingActiveResponse.value = false
		})
}

onBeforeMount(() => {
	getAvailableIntegrations()
})
</script>

<style lang="scss" scoped>
.active-response-list {
	.list {
		container-type: inline-size;
		min-height: 200px;
	}
}
</style>
