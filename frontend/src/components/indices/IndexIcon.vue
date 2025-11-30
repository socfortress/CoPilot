<template>
	<span class="index-icon" :class="[`health-${health}`, { color }]">
		<Icon v-if="health === IndexHealth.GREEN" :name="ShieldIcon" :size="18" />
		<Icon v-if="health === IndexHealth.YELLOW" :name="WarningIcon" :size="18" />
		<Icon v-if="health === IndexHealth.RED" :name="DangerIcon" :size="18" />
	</span>
</template>

<script setup lang="ts">
import type { IndexStats } from "@/types/indices.d"
import { toRefs } from "vue"
import Icon from "@/components/common/Icon.vue"
import { IndexHealth } from "@/types/indices.d"

const props = defineProps<{
	health: IndexStats["health"]
	color?: boolean
}>()
const ShieldIcon = "majesticons:shield-check-line"
const WarningIcon = "majesticons:shield-exclamation-line"
const DangerIcon = "majesticons:exclamation-line"

const { health, color } = toRefs(props)
</script>

<style lang="scss" scoped>
.index-icon {
	display: flex;
	align-items: center;
	&.color {
		&.health-green {
			color: var(--success-color);
		}

		&.health-yellow {
			color: var(--warning-color);
		}

		&.health-red {
			color: var(--error-color);
		}
	}
}
</style>
