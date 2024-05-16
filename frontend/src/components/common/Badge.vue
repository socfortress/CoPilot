<template>
	<component
		:is="!!href ? 'a' : 'div'"
		class="badge"
		:href="href"
		:class="[type, color, { 'cursor-help': hintCursor, 'cursor-pointer': pointCursor, fluid }]"
	>
		<span v-if="$slots.label || $slots.iconLeft || $slots.iconRight" class="flex items-center gap-2">
			<slot name="iconLeft"></slot>
			<slot name="label"></slot>
			<slot name="iconRight"></slot>
		</span>
		<span v-if="$slots.value">
			<slot name="value"></slot>
		</span>
	</component>
</template>

<script setup lang="ts">
// TODO: refactor
const { type, hintCursor, pointCursor, color, href, fluid } = defineProps<{
	type?: "splitted" | "muted" | "active" | "cursor"
	hintCursor?: boolean
	pointCursor?: boolean
	fluid?: boolean
	color?: "danger" | "warning" | "success"
	href?: string
}>()
</script>

<style lang="scss" scoped>
.badge {
	border-radius: var(--border-radius);
	border: var(--border-small-100);
	display: flex;
	align-items: center;
	font-size: 14px;
	padding: 0px 6px;
	height: 26px;
	line-height: 1;
	gap: 6px;
	transition: all 0.3s var(--bezier-ease);

	&.muted {
		span,
		i {
			opacity: 0.5;
		}
	}

	&.active {
		color: var(--success-color);
		background-color: var(--success-005-color);
		border-color: var(--success-color);
	}

	&.cursor {
		cursor: pointer;

		&:hover {
			color: var(--primary-color);
			border-color: var(--primary-color);
		}
	}

	span:not(:last-child) {
		border-right: var(--border-small-100);
	}

	&.splitted {
		padding: 0px;
		gap: 0;
		overflow: hidden;

		& > span {
			padding: 0px 8px;
			height: 100%;
			line-height: 24px;

			&:first-child {
				background-color: var(--primary-005-color);
				line-height: 1.1;
				white-space: nowrap;
			}
			&:last-child {
				font-family: var(--font-family-mono);
				font-size: 0.9em;
			}
		}

		&.danger {
			& > span {
				&:first-child {
					background-color: var(--secondary4-opacity-010-color);
				}
			}
		}
		&.warning {
			& > span {
				&:first-child {
					background-color: var(--secondary3-opacity-010-color);
				}
			}
		}

		&.success {
			& > span {
				&:first-child {
					background-color: var(--success-005-color);
				}
			}
		}
	}

	&.fluid {
		min-height: 26px;
		height: unset;

		&.splitted {
			& > span {
				&:last-child {
					line-height: 1.1;
					padding-top: 5px;
					padding-bottom: 5px;
					display: flex;
					align-items: center;
				}
			}
		}
	}
}
</style>
