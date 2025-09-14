<template>
	<Icon :name="getTechnologyIcon(action.technology)" :size />
</template>

<script setup lang="ts">
import type { ActiveResponseItem } from "@/types/copilotAction.d"
import Icon from "@/components/common/Icon.vue"
import { iconFromOs } from "@/utils"

const { action, size = 14 } = defineProps<{ action: ActiveResponseItem; size?: number }>()

function getTechnologyIcon(technology: string): string {
	if (
		technology.toLowerCase().includes("win") ||
		technology.toLowerCase().includes("lin") ||
		technology.toLowerCase().includes("mac")
	) {
		return iconFromOs(technology)
	}

	if (technology.toLowerCase().includes("wazuh")) {
		return "carbon:security"
	}
	if (technology.toLowerCase().includes("velociraptor")) {
		return "fluent-emoji-high-contrast:eagle"
	}
	if (technology.toLowerCase().includes("network")) {
		return "carbon:network-3"
	}
	if (technology.toLowerCase().includes("cloud")) {
		return "carbon:cloud"
	}

	return "carbon:application"
}
</script>
