<template>
	<n-input-group>
		<n-select
			v-model:value="model.key"
			:data-testid="`${testid}-filter-key`"
			:options="keyOptions"
			clearable
			placeholder="Filter key"
			class="min-w-20 basis-1/2"
			:consistent-menu-width="false"
		/>
		<n-select
			v-model:value="model.value"
			:data-testid="`${testid}-filter-value`"
			:disabled="!model.key"
			:options="valueOptions"
			:remote="isSearchKey"
			:loading="searching"
			filterable
			clearable
			placeholder="Filter value"
			class="min-w-20 basis-1/2"
			:consistent-menu-width="false"
			@search="onSearch"
		/>
	</n-input-group>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import { useDebounceFn } from "@vueuse/core"
import { NInputGroup, NSelect, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { getApiErrorMessage } from "@/utils"

/**
 * A "filter by <key> = <value>" picker shared by the portal lists.
 *
 * The keys and their values come from `loadOptions`. A key whose values are too many to
 * download (the alerts' asset names) can be named `searchKey`: its values are then
 * searched on the server as the user types, through `search`, and it is always offered.
 */

export interface KeyValueFilterModel {
	key: string | null
	value: string | null
}

const props = defineProps<{
	/** Prefix of the `data-testid`s: `<testid>-filter-key` and `<testid>-filter-value`. */
	testid: string
	loadOptions: () => Promise<Record<string, string[]>>
	searchKey?: string
	search?: (term: string | null, signal: AbortSignal) => Promise<string[]>
	/** How a value reads in the picker (the value sent stays the raw one). */
	valueLabel?: (key: string, value: string) => string
}>()

const emit = defineEmits<{
	(e: "loaded", value: Record<string, string[]>): void
}>()

const model = defineModel<KeyValueFilterModel>("value", { required: true })
const message = useMessage()
const options = ref<Record<string, string[]>>({})
const searchResults = ref<string[]>([])
const { loading: searching, run } = useLatestRequest()

const isSearchKey = computed(() => !!props.searchKey && model.value.key === props.searchKey)

const keyOptions = computed(() => {
	const keys = Object.entries(options.value)
		.filter(([key, values]) => key !== props.searchKey && values.length > 0)
		.map(([key]) => key)
	if (props.searchKey) keys.push(props.searchKey)
	return keys.map(key => ({ label: key, value: key }))
})

const valueOptions = computed(() => {
	const values = isSearchKey.value ? searchResults.value : model.value.key ? options.value[model.value.key] : []
	const { key } = model.value
	const { valueLabel } = props
	return (values || []).map(value => ({ label: valueLabel && key ? valueLabel(key, value) : value, value }))
})

function searchValues(term: string | null) {
	const search = props.search
	if (!search) return
	return run(
		async signal => {
			searchResults.value = await search(term, signal)
		},
		err => message.error(getApiErrorMessage(err as ApiError))
	)
}

// Typing is the one input worth debouncing.
const onSearch = useDebounceFn((term: string) => {
	if (isSearchKey.value) searchValues(term)
}, 300)

async function loadOptions() {
	try {
		options.value = await props.loadOptions()
		emit("loaded", options.value)
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	}
}

watch(
	() => model.value.key,
	key => {
		model.value.value = null
		if (props.searchKey && key === props.searchKey) searchValues(null)
	}
)

onBeforeMount(loadOptions)
</script>
