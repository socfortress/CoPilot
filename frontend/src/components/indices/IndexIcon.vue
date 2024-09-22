<template>
	<span class="index-icon" :class="[`health-${health}`, { color }]">
		<Icon v-if="health === IndexHealth.GREEN" :name="ShieldIcon" :size="18"></Icon>
		<Icon v-if="health === IndexHealth.YELLOW" :name="WarningIcon" :size="18"></Icon>
		<Icon v-if="health === IndexHealth.RED" :name="DangerIcon" :size="18"></Icon>
	</span>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import { IndexHealth, type IndexStats } from "@/types/indices.d"
import { toRefs } from "vue"

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
