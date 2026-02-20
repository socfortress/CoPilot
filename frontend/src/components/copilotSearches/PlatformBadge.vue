<template>
	<Badge :color="getPlatformColor(platform)">
		<template #iconLeft>
			<Icon :name="getPlatformIcon(platform)" :size="14" />
		</template>
		<template #value>
			<span class="whitespace-nowrap">{{ platform }}</span>
		</template>
	</Badge>
</template>

<script setup lang="ts">
import type { BadgeColor } from "@/components/common/Badge.vue"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"

const { platform } = defineProps<{ platform: string }>()

function getPlatformColor(platform: string): BadgeColor | undefined {
	const p = platform.toLowerCase()
	if (p.includes("linux")) return "warning"
	if (p.includes("windows")) return "primary"
	if (p.includes("macos") || p.includes("darwin")) return "success"
	return undefined
}

function getPlatformIcon(platform: string): string {
	const p = platform.toLowerCase()
	if (p.includes("linux")) return "carbon:logo-linux"
	if (p.includes("windows")) return "carbon:logo-windows"
	if (p.includes("macos") || p.includes("darwin")) return "carbon:logo-apple"
	return "carbon:application"
}
</script>
