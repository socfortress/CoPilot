<template>
	<Badge :color="getTechnologyColor(action.technology)">
		<template #iconLeft><TechnologyIcon :action :size="14" /></template>
		<template #value>
			<span class="whitespace-nowrap">{{ action.technology }}</span>
		</template>
	</Badge>
</template>

<script setup lang="ts">
import type { BadgeColor } from "@/components/common/Badge.vue"
import type { CopilotAction } from "@/types/copilotAction.d"
import Badge from "@/components/common/Badge.vue"
import TechnologyIcon from "./TechnologyIcon.vue"

const { action } = defineProps<{ action: CopilotAction }>()

function getTechnologyColor(technology: string): BadgeColor | undefined {
	if (technology.toLowerCase().includes("win")) {
		return "primary"
	}
	if (technology.toLowerCase().includes("lin")) {
		return "warning"
	}
	if (technology.toLowerCase().includes("mac")) {
		return "success"
	}
	if (technology.toLowerCase().includes("wazuh")) {
		return "success"
	}
	if (technology.toLowerCase().includes("velociraptor")) {
		return "primary"
	}
	if (technology.toLowerCase().includes("network")) {
		return "primary"
	}
	if (technology.toLowerCase().includes("cloud")) {
		return "success"
	}

	return undefined
}
</script>
