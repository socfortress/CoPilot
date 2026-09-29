<template>
	<n-input-group>
		<n-select
			v-model:value="model.key"
			data-testid="alerts-filter-key"
			:options="filtersKeysOptions"
			clearable
			placeholder="Filter key"
			class="min-w-20 basis-1/2"
			:consistent-menu-width="false"
		/>
		<n-select
			v-model:value="model.value"
			data-testid="alerts-filter-value"
			:disabled="!model.key"
			:options="filtersValuesOptions"
			:remote="isAssetKey"
			:loading="assetsLoading"
			filterable
			clearable
			placeholder="Filter value"
			class="min-w-20 basis-1/2"
			:consistent-menu-width="false"
			@search="searchAssets"
		/>
	</n-input-group>
</template>

<script setup lang="ts">
import type { AlertsFilters } from "@/types/alerts"
import type { ApiError } from "@/types/common"
import { useDebounceFn } from "@vueuse/core"
import axios from "axios"
import _pick from "lodash/pick"
import { NInputGroup, NSelect, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"

export interface FiltersModel {
	key: string | null
	value: string | null
}

// Asset names are not in the filter options (a large tenant has thousands): the asset
// filter searches the server as the user types instead.
const ASSETS_KEY = "assets"

const model = defineModel<FiltersModel>("value", { required: true })
const filters = ref<Record<string, string[]>>({})
const assetOptions = ref<string[]>([])
const assetsLoading = ref(false)
const isAssetKey = computed(() => model.value.key === ASSETS_KEY)

const filtersKeysOptions = computed(() => [
	...Object.entries(filters.value || {})
		.filter(([key, value]) => key !== ASSETS_KEY && value.length > 0)
		.map(([key]) => ({ label: key, value: key })),
	{ label: ASSETS_KEY, value: ASSETS_KEY }
])
const filtersValuesOptions = computed(() => {
	const values = isAssetKey.value ? assetOptions.value : model.value.key ? filters.value[model.value.key] : []
	return (values || []).map(value => ({ label: value, value }))
})
const message = useMessage()

let assetsController = new AbortController()

async function loadAssets(search: string | null) {
	assetsController.abort()
	assetsController = new AbortController()
	assetsLoading.value = true
	try {
		const response = await Api.alerts.searchAlertAssets(search, assetsController.signal)
		assetOptions.value = response.data.assets
		assetsLoading.value = false
	} catch (err) {
		if (!axios.isCancel(err)) {
			message.error(getApiErrorMessage(err as ApiError))
			assetsLoading.value = false
		}
	}
}

// Typing is the one input worth debouncing.
const searchAssets = useDebounceFn((search: string) => {
	if (isAssetKey.value) loadAssets(search)
}, 300)

async function loadFilters() {
	try {
		const response = await Api.alerts.getAlertsFilters()
		filters.value = _pick<AlertsFilters, keyof AlertsFilters>(response.data, ["sources", "statuses", "tags"])
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	}
}

watch(
	() => model.value.key,
	key => {
		model.value.value = null
		if (key === ASSETS_KEY) loadAssets(null)
	}
)

onBeforeMount(() => {
	loadFilters()
})
</script>
