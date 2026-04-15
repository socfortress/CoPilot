<template>
	<div class="grid grid-cols-1 items-center gap-6 @xl:grid-cols-2 @4xl:grid-cols-4">
		<div>
			<n-select
				v-model:value="filters.status"
				:options="statusOptions"
				placeholder="Status"
				:consistent-menu-width="false"
			/>
		</div>
		<div>
			<n-select
				v-model:value="filters.os"
				:options="osOptions"
				placeholder="Operating System"
				:consistent-menu-width="false"
			/>
		</div>
		<div>
			<n-input v-model:value="filters.search" placeholder="Search..." clearable />
		</div>
		<div>
			<n-checkbox v-model:checked="filters.critical">Only Critical Assets</n-checkbox>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { AgentStatus } from "@/types/agents"
import { NCheckbox, NInput, NSelect } from "naive-ui"
import { computed } from "vue"

export interface AgentsFilters {
	status: AgentStatus | null
	critical: boolean
	os: string | null
	search: string | null
}

const props = defineProps<{
	status: AgentStatus[]
	os: string[]
}>()

const filters = defineModel<AgentsFilters>("value", { required: true })

const statusOptions = computed(() => {
	return props.status.map(status => ({ label: status, value: status }))
})

const osOptions = computed(() => {
	return props.os.map(os => ({ label: os, value: os }))
})
</script>
