<template>
	<div>
		<div v-for="item of healthyList" :key="item.id">
			<pre>{{ item }}</pre>
		</div>
		<div v-for="item of unhealthyList" :key="item.id">
			<pre>{{ item }}</pre>
		</div>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import { h, onBeforeMount, ref, toRefs } from "vue"
import KVCard from "@/components/common/KVCard.vue"
import _get from "lodash/get"
import Api from "@/api"
import { useMessage, NButton, useDialog } from "naive-ui"
import type { CustomerAgentHealth } from "@/types/customers.d"

const { type, customerCode } = defineProps<{
	type: "wazuh" | "velociraptor"
	customerCode: string
}>()

const EditIcon = "uil:edit-alt"
const DeleteIcon = "ph:trash"
const AddIcon = "carbon:add-alt"

const loading = ref(false)
const healthyList = ref<CustomerAgentHealth[]>([])
const unhealthyList = ref<CustomerAgentHealth[]>([])
const message = useMessage()

function getList() {
	loading.value = true

	const params = {
		method: "" as "getCustomerAgentsHealthcheckWazuh" | "getCustomerAgentsHealthcheckVelociraptor",
		healthy: "",
		unhealthy: ""
	}

	switch (type) {
		case "wazuh":
			params.method = "getCustomerAgentsHealthcheckWazuh"
			params.healthy = "healthy_wazuh_agents"
			params.unhealthy = "unhealthy_wazuh_agents"
			break
		case "velociraptor":
			params.method = "getCustomerAgentsHealthcheckVelociraptor"
			params.healthy = "healthy_velociraptor_agents"
			params.unhealthy = "unhealthy_velociraptor_agents"
			break
	}

	if (!params.method) {
		return
	}

	Api.customers[params.method](customerCode)
		.then(res => {
			if (res.data.success) {
				healthyList.value = _get(res, `data.${params.healthy}`, [])
				unhealthyList.value = _get(res, `data.${params.unhealthy}`, [])
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
	getList()
})
</script>
