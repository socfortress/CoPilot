<template>
	<n-spin :show="loading">
		<div class="customer-healthcheck-list">
			<div class="list flex flex-col gap-2 p-6 pt-4" v-if="healthyList.length">
				<div class="title healthy flex items-center gap-2">
					<Icon :name="CheckIcon" :size="16"></Icon>
					Healthy
					<code>{{ healthyList.length }}</code>
				</div>
				<CustomerHealthcheckItem
					v-for="item of healthyList"
					:key="item.id"
					:health-data="item"
					:source="source"
					type="healthy"
					bg-secondary
					class="item-appear item-appear-bottom item-appear-005"
				/>
			</div>
			<div class="list flex flex-col gap-2 p-6 pt-4" v-if="unhealthyList.length">
				<div class="title unhealthy flex items-center gap-2">
					<Icon :name="AlertIcon" :size="16"></Icon>
					Unhealthy
					<code>{{ unhealthyList.length }}</code>
				</div>
				<CustomerHealthcheckItem
					v-for="item of unhealthyList"
					:key="item.id"
					:health-data="item"
					:source="source"
					type="unhealthy"
					bg-secondary
					class="item-appear item-appear-bottom item-appear-005"
				/>
			</div>
			<n-empty v-if="!healthyList.length && !unhealthyList.length && !loading" class="justify-center h-48" />
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import { h, onBeforeMount, ref, toRefs } from "vue"
import KVCard from "@/components/common/KVCard.vue"
import _get from "lodash/get"
import Api from "@/api"
import CustomerHealthcheckItem from "./CustomerHealthcheckItem.vue"
import { useMessage, NButton, useDialog, NSpin, NEmpty } from "naive-ui"
import type { CustomerAgentHealth, CustomerHealthcheckSource } from "@/types/customers.d"

const { source, customerCode } = defineProps<{
	source: CustomerHealthcheckSource
	customerCode: string
}>()

const EditIcon = "uil:edit-alt"
const CheckIcon = "carbon:checkmark-outline"
const DeleteIcon = "ph:trash"
const AlertIcon = "mdi:alert-outline"
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

	switch (source) {
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

<style lang="scss" scoped>
.customer-healthcheck-list {
	min-height: 200px;

	.list {
		.title {
			margin-bottom: 10px;

			&.healthy {
				color: var(--primary-color);
			}
			&.unhealthy {
				color: var(--warning-color);
			}
		}

		&:not(:last-child) {
			margin-bottom: 20px;
		}
	}
}
</style>
