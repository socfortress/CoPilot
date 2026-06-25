<template>
	<div class="flex w-80! flex-col gap-3 py-1">
		<div class="px-3">
			<small class="text-secondary">Filter audit log by:</small>
		</div>

		<div class="flex flex-col gap-2 px-3">
			<n-select
				v-model:value="local.action"
				:options="actionOptions"
				placeholder="Action"
				size="small"
				clearable
				filterable
			/>
			<n-select
				v-model:value="local.result"
				:options="resultOptions"
				placeholder="Result"
				size="small"
				clearable
			/>
			<n-input v-model:value="local.actor_username" placeholder="Actor username" size="small" clearable />
			<n-input v-model:value="local.entity_type" placeholder="Entity type (e.g. agent, user)" size="small" clearable />
			<n-input v-model:value="local.customer_code" placeholder="Customer code" size="small" clearable />
			<n-input v-model:value="local.search" placeholder="Search (details / username / entity)" size="small" clearable />
			<n-date-picker
				v-model:value="local.dateRange"
				type="datetimerange"
				size="small"
				clearable
				placeholder="Date range"
			/>
		</div>

		<div class="flex justify-between gap-2 px-3">
			<n-button size="small" quaternary @click="reset()">Reset</n-button>
			<div class="flex gap-2">
				<n-button size="small" secondary @click="close()">Close</n-button>
				<n-button size="small" type="primary" secondary @click="submit()">Apply</n-button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { AuditUiFilters } from "@/types/audit.d"
import _cloneDeep from "lodash/cloneDeep"
import { NButton, NDatePicker, NInput, NSelect } from "naive-ui"
import { onBeforeMount, ref } from "vue"

const props = defineProps<{ actions: string[]; results: string[] }>()

const emit = defineEmits<{
	(e: "close"): void
	(e: "submit"): void
}>()

const filters = defineModel<AuditUiFilters>("filters", { required: true })

function emptyFilters(): AuditUiFilters {
	return {
		action: null,
		result: null,
		entity_type: null,
		actor_username: null,
		customer_code: null,
		search: null,
		dateRange: null
	}
}

const local = ref<AuditUiFilters>(emptyFilters())

const actionOptions = props.actions.map(a => ({ label: a, value: a }))
const resultOptions = props.results.map(r => ({ label: r, value: r }))

function close() {
	emit("close")
}

function reset() {
	local.value = emptyFilters()
	filters.value = _cloneDeep(local.value)
	emit("submit")
}

function submit() {
	// Normalise empty strings to null so they don't become no-op query params.
	const normalised: AuditUiFilters = { ...local.value }
	for (const key of ["action", "result", "entity_type", "actor_username", "customer_code", "search"] as const) {
		if (!normalised[key]) normalised[key] = null
	}
	filters.value = _cloneDeep(normalised)
	emit("submit")
}

onBeforeMount(() => {
	local.value = _cloneDeep(filters.value) ?? emptyFilters()
})
</script>
