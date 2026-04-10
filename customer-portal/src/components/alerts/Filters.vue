<template>
	<n-input-group>
		<n-select
			v-model:value="model.key"
			:options="filtersKeysOptions"
			clearable
			placeholder="Filter key"
			class="basis-1/2"
		/>
		<n-select
			v-model:value="model.value"
			:options="filtersValuesOptions"
			filterable
			clearable
			placeholder="Filter value"
			class="basis-1/2"
		/>
	</n-input-group>
</template>

<script setup lang="ts">
import type { AlertsFilters } from "@/api/endpoints/alerts"
import type { ApiError } from "@/types/common"
import _pick from "lodash/pick"
import { NInputGroup, NSelect, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"

export interface FiltersModel {
	key: string | null
	value: string | null
}

const model = defineModel<FiltersModel>("value", { required: true })
const filters = ref<Record<string, string[]>>({})
const filtersKeysOptions = computed(
	() =>
		Object.keys(filters.value || {}).map(key => ({
			label: key,
			value: key
		})) || []
)
const filtersValuesOptions = computed(
	() => filters.value[model.value.key]?.map(value => ({ label: value, value })) || []
)
const message = useMessage()

async function loadFilters() {
	try {
		const response = await Api.alerts.getAlertsFilters()
		filters.value = _pick<AlertsFilters, keyof AlertsFilters>(response.data, [
			"sources",
			"assets",
			"statuses",
			"tags"
		])
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	}
}

onBeforeMount(() => {
	loadFilters()
})
</script>
