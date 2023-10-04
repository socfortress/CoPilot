<template>
	<span class="index-icon" :class="[`health-${health}`, { color }]">
		<n-icon v-if="health === IndexHealth.GREEN" :size="18">
			<ShieldIcon />
		</n-icon>
		<n-icon v-if="health === IndexHealth.YELLOW">
			<WarningIcon />
		</n-icon>
		<n-icon v-if="health === IndexHealth.RED">
			<DangerIcon />
		</n-icon>
	</span>
</template>

<script setup lang="ts">
import { toRefs } from "vue"
import { type Index, IndexHealth } from "@/types/indices.d"
import ShieldIcon from "@vicons/fluent/ShieldTask20Regular"
import WarningIcon from "@vicons/fluent/ShieldError20Regular"
import DangerIcon from "@vicons/fluent/Warning20Regular"
import { NIcon } from "naive-ui"

const props = defineProps<{
	health: Index["health"]
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
