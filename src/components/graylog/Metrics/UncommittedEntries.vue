<template>
	<div class="uncommitted-entries-wrap">
		<div class="line"></div>
		<div class="uncommitted-entries">
			<div class="label flex items-center gap-3">
				<Icon :name="DangerIcon" v-if="isWarning"></Icon>
				<span>Uncommitted Journal Entries</span>
			</div>
			<div class="value" :class="{ warning: isWarning }">
				<span>{{ value }}</span>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
// TODO:  add a realtime chart
// TODO: add goto grylog message page button

import Icon from "@/components/common/Icon.vue"
import { computed, toRefs } from "vue"

const props = defineProps<{
	value: number
}>()
const { value } = toRefs(props)

const DangerIcon = "majesticons:exclamation-line"

const isWarning = computed<boolean>(() => {
	return value.value > 50000
})
</script>

<style lang="scss" scoped>
.uncommitted-entries-wrap {
	width: 100%;
	position: relative;
	.line {
		width: 100%;
		height: 1px;
		background: var(--divider-010-color);
		background: linear-gradient(
			90deg,
			transparent 0%,
			var(--divider-010-color) 5%,
			var(--divider-010-color) 95%,
			transparent 100%
		);
		position: absolute;
		top: 50%;
	}

	.uncommitted-entries {
		position: relative;
		background-color: var(--bg-color);
		display: flex;
		border-radius: var(--border-radius);
		border: var(--border-small-050);
		overflow: hidden;
		max-width: 400px;
		margin: 0 auto;

		.label {
			padding: 18px 22px;
			font-size: 18px;
			flex-grow: 1;
			font-weight: 700;

			i {
				color: var(--secondary3-color);
			}
		}
		.value {
			padding: 18px 22px;
			background-color: var(--bg-secondary-color);
			font-size: 20px;
			font-family: var(--font-family-mono);

			&.warning {
				color: var(--secondary3-color);
				background-color: var(--secondary3-opacity-005-color);
			}
		}
	}
}
</style>
