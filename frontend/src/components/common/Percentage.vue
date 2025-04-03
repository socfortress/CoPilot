<template>
	<div
		class="percentage flex items-center gap-2"
		:class="[
			{
				color: useColor,
				'with-background': useBackground,
				'opacity-50': useOpacity
			},
			direction
		]"
	>
		<span v-if="progress && progress === 'line'" class="progress">
			<n-progress
				type="line"
				:status="direction === 'up' ? 'success' : 'error'"
				:percentage="value"
				:show-indicator="false"
				:stroke-width="18"
				class="!w-12"
			/>
		</span>
		<span v-if="icon && icon === 'arrow'" class="percentage-icon flex items-center">
			<Icon v-if="direction === 'up'" :name="ChevronUp" />
			<Icon v-if="direction === 'down'" :name="ChevronDown" />
		</span>
		<span v-if="icon && icon === 'operator'" class="percentage-icon">
			{{ direction === "up" ? "+" : "-" }}
		</span>
		<span>{{ value }}%</span>
		<span v-if="progress && progress === 'circle'" class="progress flex items-center">
			<n-progress
				type="circle"
				:status="direction === 'up' ? 'success' : 'error'"
				:percentage="value"
				:show-indicator="false"
				:stroke-width="18"
				class="w-5!"
			/>
		</span>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import { NProgress } from "naive-ui"

export interface PercentageProps {
	value: number
	useColor?: boolean
	useOpacity?: boolean
	useBackground?: boolean
	progress?: "line" | "circle" | false
	icon?: "arrow" | "operator" | false
	direction?: "up" | "down"
}

const {
	value,
	direction,
	useColor = true,
	useBackground = false,
	useOpacity = false,
	icon = "arrow",
	progress = false
} = defineProps<PercentageProps>()

const ChevronUp = "tabler:chevron-up"
const ChevronDown = "tabler:chevron-down"
</script>

<style scoped lang="scss">
.percentage {
	white-space: nowrap;
	font-family: var(--font-family-mono);
	font-size: 14px;
	line-height: 1.7;

	.percentage-icon {
		margin-right: 3px;
	}

	&.color {
		&.up {
			color: var(--success-color);
		}
		&.down {
			color: var(--error-color);
		}
	}

	&.with-background {
		position: relative;
		padding: 1px 4px;
		padding-right: 6px;
		font-size: 11px;

		&::before {
			content: "";
			display: block;
			position: absolute;
			width: 100%;
			height: 100%;
			opacity: 0.1;
			border-radius: var(--border-radius-small);
			top: 0;
			left: 0;
		}

		&.up {
			color: var(--success-color);
			&::before {
				background-color: var(--success-color);
			}
		}
		&.down {
			color: var(--error-color);
			&::before {
				background-color: var(--error-color);
			}
		}
	}
}
</style>
