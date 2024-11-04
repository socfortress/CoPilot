<template>
	<div
		class="collapse-box"
		:style="arrowOffset ? `--arrow-offset: ${arrowOffset}` : undefined"
		:class="[arrow ? `arrow arrow-${arrow}` : undefined, { show, embedded }]"
	>
		<div>
			<slot />
		</div>
	</div>
</template>

<script setup lang="ts">
const { show, embedded, arrow, arrowOffset } = defineProps<{
	show: boolean
	embedded?: boolean
	arrow?: "top-left" | "top-right" | "top"
	arrowOffset?: string
}>()
</script>

<style lang="scss" scoped>
.collapse-box {
	--transition-time: 0.3s;
	--arrow-size: 10px;
	--arrow-offset: 8px;
	overflow: hidden;
	display: grid;
	grid-template-rows: 0fr;
	padding-top: 0px;
	opacity: 0;
	position: relative;
	transition:
		opacity var(--transition-time) var(--bezier-ease),
		grid-template-rows var(--transition-time) var(--bezier-ease),
		padding-top var(--transition-time) var(--bezier-ease);

	&.arrow-top,
	&.arrow-top-left,
	&.arrow-top-right {
		&::after {
			content: "";
			width: 0;
			height: 0;
			border-left: var(--arrow-size) solid transparent;
			border-right: var(--arrow-size) solid transparent;
			border-bottom: var(--arrow-size) solid var(--bg-secondary-color);
			position: absolute;
			transition: transform var(--transition-time) var(--bezier-ease);

			top: 2px;
			transform: rotateX(90deg);
			transform-origin: top center;
		}
	}
	&.arrow-top {
		&::after {
			margin-left: calc(var(--arrow-size) / -2);
			left: 50%;
		}
	}
	&.arrow-top-left {
		&::after {
			left: var(--arrow-offset);
			right: initial;
		}
	}
	&.arrow-top-right {
		&::after {
			right: var(--arrow-offset);
			left: initial;
		}
	}

	& > * {
		overflow: hidden;
	}

	&.embedded > * {
		background-color: var(--bg-secondary-color);
		border-radius: var(--border-radius);
	}

	&.show {
		grid-template-rows: 1fr;
		opacity: 1;

		&.arrow {
			@apply pt-3;

			&::after {
				transform: rotateX(0deg);
			}
		}
	}
}
</style>
