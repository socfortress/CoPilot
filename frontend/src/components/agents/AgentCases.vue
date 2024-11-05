<template>
	<n-spin :show="loading">
		<div class="header flex items-center justify-end gap-2">
			<div class="info flex grow gap-5">
				<div class="box">
					Total:
					<code>{{ casesList.length }}</code>
				</div>
			</div>
		</div>
		<div class="my-3 flex min-h-52 flex-col gap-2">
			<template v-if="casesList.length">
				<SocCaseItem
					v-for="item of casesList"
					:key="item"
					:case-id="item"
					class="item-appear item-appear-bottom item-appear-005"
					@deleted="getData()"
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
import Api from "@/api"
import SocCaseItem from "@/components/soc/SocCases/SocCaseItem.vue"
import axios from "axios"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, onBeforeUnmount, ref, toRefs } from "vue"

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
