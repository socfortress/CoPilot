<template>
	<Badge :color="getSeverityColor(severity)">
		<template #iconLeft>
			<Icon :name="getSeverityIcon(severity)" :size="14" />
		</template>
		<template #value>
			<span class="whitespace-nowrap">{{ severity }}</span>
		</template>
	</Badge>
</template>

<script setup lang="ts">
import type { BadgeColor } from "@/components/common/Badge.vue"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"

const { severity } = defineProps<{ severity: string }>()

function getSeverityColor(severity: string): BadgeColor | undefined {
	switch (severity.toLowerCase()) {
		case "low":
			return "success"
		case "medium":
			return "warning"
		case "high":
			return "danger"
		case "critical":
			return "danger"
		default:
			return undefined
	}
}

function getSeverityIcon(severity: string): string {
	switch (severity.toLowerCase()) {
		case "low":
			return "carbon:warning-alt"
		case "medium":
			return "carbon:warning"
		case "high":
			return "carbon:warning-filled"
		case "critical":
			return "carbon:error-filled"
		default:
			return "carbon:warning"
	}
}
</script>
