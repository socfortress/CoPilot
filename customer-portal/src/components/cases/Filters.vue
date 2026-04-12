<template>
	<n-input-group>
		<n-select
			v-model:value="model.key"
			:options="filtersKeysOptions"
			clearable
			placeholder="Filter key"
			class="basis-1/2"
			:consistent-menu-width="false"
		/>
		<n-select
			v-model:value="model.value"
			:disabled="!model.key"
			:options="filtersValuesOptions"
			filterable
			clearable
			placeholder="Filter value"
			class="basis-1/2"
			:consistent-menu-width="false"
		/>
	</n-input-group>
</template>

<script setup lang="ts">
import type { CasesFilters } from "@/types/cases"
import type { ApiError } from "@/types/common"
import _pick from "lodash/pick"
import { NInputGroup, NSelect, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"

export interface FiltersModel {
	key: string | null
	value: string | null
}

const emit = defineEmits<{
	(e: "loaded", value: Record<string, string[]>): void
}>()

const model = defineModel<FiltersModel>("value", { required: true })
const filters = ref<Record<string, string[]>>({})
const filtersKeysOptions = computed(
	() =>
		Object.entries(filters.value || {})
			.filter(([_key, value]) => value.length > 0)
			.map(([key]) => ({
				label: key,
				value: key
			})) || []
)
const filtersValuesOptions = computed(() =>
	model.value.key ? filters.value[model.value.key]?.map(value => ({ label: value, value })) || [] : []
)
const message = useMessage()

async function loadFilters() {
	try {
		const response = await Api.cases.getCasesFilters()
		filters.value = _pick<CasesFilters, keyof CasesFilters>(response.data, ["assigned_to", "status"])
		emit("loaded", filters.value)
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	}
}

watch(
	() => model.value.key,
	() => {
		model.value.value = null
	}
)

onBeforeMount(() => {
	loadFilters()
})
</script>
