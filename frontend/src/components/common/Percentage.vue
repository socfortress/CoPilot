<template>
	<div
		class="percentage flex items-center"
		:class="[
			{
				color: useColor,
				'with-background': useBackground,
				'opacity-50': useOpacity
			},
			direction
		]"
	>
		<span class="progress mr-3" v-if="progress && progress === 'line'">
			<n-progress
				type="line"
				:status="direction === 'up' ? 'success' : 'error'"
				:percentage="value"
				:show-indicator="false"
				:stroke-width="18"
				style="width: 50px"
			/>
		</span>
		<span v-if="icon && icon === 'arrow'" class="flex items-center percentage-icon">
			<Icon v-if="direction === 'up'" :name="ChevronUp"></Icon>
			<Icon v-if="direction === 'down'" :name="ChevronDown"></Icon>
		</span>
		<span v-if="icon && icon === 'operator'" class="percentage-icon">
			{{ direction === "up" ? "+" : "-" }}
		</span>
		<span>{{ value }}%</span>
		<span class="progress ml-3 flex items-center" v-if="progress && progress === 'circle'">
			<n-progress
				type="circle"
				:status="direction === 'up' ? 'success' : 'error'"
				:percentage="value"
				:show-indicator="false"
				:stroke-width="18"
				style="width: 22px"
			/>
		</span>
	</div>
</template>

<script setup lang="ts">
import { toRefs } from "vue"
import { NProgress } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

const ChevronUp = "tabler:chevron-up"
const ChevronDown = "tabler:chevron-down"

export interface PercentageProps {
	value: number
	useColor?: boolean
	useOpacity?: boolean
	useBackground?: boolean
	progress?: "line" | "circle" | false
	icon?: "arrow" | "operator" | false
	direction?: "up" | "down"
}

const props = withDefaults(defineProps<PercentageProps>(), {
	useColor: true,
	useBackground: false,
	useOpacity: false,
	icon: "arrow",
	progress: false
})
const { value, useColor, useBackground, useOpacity, icon, progress, direction } = toRefs(props)
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
