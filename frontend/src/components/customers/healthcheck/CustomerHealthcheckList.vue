<template>
	<div class="mb-6 flex justify-end">
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
		<div class="flex min-h-52 flex-col gap-6">
			<div v-if="healthyList.length" class="flex flex-col gap-2 [&:not(:last-child)]:mb-5">
				<div class="text-primary mb-2 flex items-center gap-2">
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
					embedded
					class="item-appear item-appear-bottom item-appear-005"
				/>
			</div>
			<div v-if="unhealthyList.length" class="flex flex-col gap-2 [&:not(:last-child)]:mb-5">
				<div class="text-warning mb-2 flex items-center gap-2">
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
					embedded
					class="item-appear item-appear-bottom item-appear-005"
				/>
			</div>
			<n-empty v-if="!healthyList.length && !unhealthyList.length && !loading" class="h-48 justify-center" />
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { CustomerAgentsHealthcheckQuery } from "@/api/endpoints/customers"
import type { CustomerAgentHealth, CustomerHealthcheckSource } from "@/types/customers.d"
import { watchDebounced } from "@vueuse/core"
import _get from "lodash/get"
import { NEmpty, NInputGroup, NInputNumber, NSelect, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import CustomerHealthcheckItem from "./CustomerHealthcheckItem.vue"

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

	let query: CustomerAgentsHealthcheckQuery | undefined
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
