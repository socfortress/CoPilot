<template>
	<span class="index-icon" :class="[`health-${health}`, { color }]">
		<Icon :name="ShieldIcon" v-if="health === IndexHealth.GREEN" :size="18"></Icon>
		<Icon :name="WarningIcon" v-if="health === IndexHealth.YELLOW" :size="18"></Icon>
		<Icon :name="DangerIcon" v-if="health === IndexHealth.RED" :size="18"></Icon>
	</span>
</template>

<script setup lang="ts">
import { toRefs } from "vue"
import { type IndexStats, IndexHealth } from "@/types/indices.d"
import Icon from "@/components/common/Icon.vue"

const ShieldIcon = "majesticons:shield-check-line"
const WarningIcon = "majesticons:shield-exclamation-line"
const DangerIcon = "majesticons:exclamation-line"

const props = defineProps<{
	health: IndexStats["health"]
	color?: boolean
}>()
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
