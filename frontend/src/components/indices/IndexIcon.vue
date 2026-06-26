<template>
	<span :class="iconClass">
		<Icon v-if="health === IndexHealth.GREEN" :name="ShieldIcon" :size="size || 18" />
		<Icon v-if="health === IndexHealth.YELLOW" :name="WarningIcon" :size="size || 18" />
		<Icon v-if="health === IndexHealth.RED" :name="DangerIcon" :size="size || 18" />
	</span>
</template>

<script setup lang="ts">
import type { IndexStats } from "@/types/indices"
import { computed, toRefs } from "vue"
import Icon from "@/components/common/Icon.vue"
import { IndexHealth } from "@/types/indices"

const props = defineProps<{
	health: IndexStats["health"]
	color?: boolean
	size?: number
}>()
const ShieldIcon = "majesticons:shield-check-line"
const WarningIcon = "majesticons:shield-exclamation-line"
const DangerIcon = "majesticons:exclamation-line"

const { health, color } = toRefs(props)

const iconClass = computed(() => {
	const base = "flex items-center"

	if (!color.value) return base

	switch (health.value) {
		case IndexHealth.GREEN:
			return `${base} text-success`
		case IndexHealth.YELLOW:
			return `${base} text-warning`
		case IndexHealth.RED:
			return `${base} text-error`
		default:
			return base
	}
})
</script>
