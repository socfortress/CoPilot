<template>
	<div class="flex flex-wrap items-center justify-end gap-2">
		<slot name="info" />

		<n-input
			v-model:value="searchQuery"
			size="small"
			placeholder="Search policies..."
			class="max-w-120 min-w-48 flex-1"
			clearable
		>
			<template #prefix>
				<Icon :name="SearchIcon" />
			</template>
		</n-input>

		<n-select
			v-model:value="selectedPlatform"
			:options="platformOptions"
			size="small"
			placeholder="Platform"
			class="max-w-45 min-w-30 flex-1"
			clearable
			:consistent-menu-width="false"
		/>
		<n-select
			v-model:value="selectedApplication"
			:options="applicationOptions"
			size="small"
			placeholder="Application"
			class="max-w-45 min-w-30 flex-1"
			clearable
			:consistent-menu-width="false"
		/>
	</div>
</template>

<script setup lang="ts">
import { NInput, NSelect } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

defineProps<{
	platformOptions: { label: string; value: string }[]
	applicationOptions: { label: string; value: string }[]
}>()

const searchQuery = defineModel<string | null>("searchQuery", { default: null })
const selectedPlatform = defineModel<string | null>("selectedPlatform", { default: null })
const selectedApplication = defineModel<string | null>("selectedApplication", { default: null })

const SearchIcon = "carbon:search"
</script>
