<template>
	<span class="index-icon" :class="[`health-${health}`, { color }]">
		<i v-if="health === IndexHealth.GREEN" class="mdi mdi-shield-check"></i>
		<i v-else-if="health === IndexHealth.YELLOW" class="mdi mdi-alert"></i>
		<i v-else-if="health === IndexHealth.RED" class="mdi mdi-alert-decagram"></i>
	</span>
</template>

<script setup lang="ts">
import { toRefs } from "vue"
import { Index, IndexHealth } from "@/types/indices.d"

const props = defineProps<{
	health: Index["health"]
	color?: boolean
}>()
const { health, color } = toRefs(props)
</script>

<style lang="scss" scoped>
@import "@/assets/scss/_variables";
@import "@/assets/scss/card-shadow";

.index-icon {
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
