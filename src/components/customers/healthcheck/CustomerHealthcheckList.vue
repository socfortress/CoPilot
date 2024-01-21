<template>
	<div class="flex mb-6 justify-end">
		<div>
			<n-input-group>
				<n-select
					v-model:value="filters.unit"
					:options="unitOptions"
					placeholder="Time unit"
					clearable
					class="!w-28"
				/>
				<n-input-number v-model:value="filters.time" :min="1" clearable placeholder="Time" class="!w-32" />
			</n-input-group>
		</div>
	</div>
	<n-spin :show="loading">
		<div class="customer-healthcheck-list flex flex-col gap-6">
			<div class="list flex flex-col gap-2" v-if="healthyList.length">
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
			<div class="list flex flex-col gap-2" v-if="unhealthyList.length">
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
import { onBeforeMount, ref, watch } from "vue"
import _get from "lodash/get"
import Api from "@/api"
import CustomerHealthcheckItem from "./CustomerHealthcheckItem.vue"
import { useMessage, NSpin, NEmpty, NSelect, NInputGroup, NInputNumber } from "naive-ui"
import type { CustomerAgentHealth, CustomerHealthcheckSource } from "@/types/customers.d"
import { watchDebounced } from "@vueuse/core"
import type { CustomerAgentsHealthcheckQuery } from "@/api/customers"

const { source, customerCode } = defineProps<{
	source: CustomerHealthcheckSource
	customerCode: string
}>()

const CheckIcon = "carbon:checkmark-outline"
const AlertIcon = "mdi:alert-outline"

const loading = ref(false)
const healthyList = ref<CustomerAgentHealth[]>([])
const unhealthyList = ref<CustomerAgentHealth[]>([])
const message = useMessage()

const unitOptions = [
	{ label: "Minutes", value: "minutes" },
	{ label: "Hours", value: "hours" },
	{ label: "Days", value: "days" }
]

const filters = ref<Partial<{ time: number; unit: "minutes" | "hours" | "days" }>>({})

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

	let query: CustomerAgentsHealthcheckQuery | undefined = undefined
	if (filters.value.time && filters.value.unit) {
		query = {}
		query[filters.value.unit] = filters.value.time
	}

	Api.customers[params.method](customerCode, query)
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

watchDebounced(
	() => filters.value.time,
	() => {
		if ((filters.value.time && filters.value.unit) || (!filters.value.time && !filters.value.unit)) {
			getList()
		}
	},
	{ debounce: 500 }
)
watch(
	() => filters.value.unit,
	() => {
		if ((filters.value.time && filters.value.unit) || (!filters.value.time && !filters.value.unit)) {
			getList()
		}
	}
)

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
