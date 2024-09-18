<template>
	<component
		:is="!!href ? 'a' : 'div'"
		class="badge"
		:href="href"
		:class="[type, color, { 'cursor-help': hintCursor, 'cursor': pointCursor, fluid, bright }]"
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
	bright?: boolean
	color?: "danger" | "warning" | "success" | "primary"
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
		padding-right: 8px;
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
				background-color: var(--divider-005-color);
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
		&.primary {
			& > span {
				&:first-child {
					background-color: var(--primary-005-color);
				}
			}
		}

		&.bright {
			&.danger {
				border-color: var(--secondary4-opacity-030-color);

				& > span {
					&:first-child {
						background-color: var(--secondary4-opacity-020-color);
					}
				}
			}
			&.warning {
				border-color: var(--secondary3-opacity-030-color);

				& > span {
					&:first-child {
						background-color: var(--secondary3-opacity-020-color);
					}
				}
			}
			&.success {
				border-color: rgba(var(--success-color-rgb), 0.3);

				& > span {
					&:first-child {
						background-color: rgba(var(--success-color-rgb), 0.2);
					}
				}
			}
			&.primary {
				border-color: var(--primary-030-color);

				& > span {
					&:first-child {
						background-color: var(--primary-020-color);
					}
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
