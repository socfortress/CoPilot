<template>
	<div class="kv-card" :class="[`kv-color-${color}`, `kv-size-${size}`]">
		<div v-if="$slots.key" class="key">
			<slot name="key"></slot>
		</div>
		<div v-if="$slots.value" class="value" :class="valueClass">
			<slot name="value"></slot>
		</div>
	</div>
</template>

<script setup lang="ts">
const { color, size, valueClass } = defineProps<{
	color?: "danger" | "warning" | "success" | "primary"
	size?: "lg"
	valueClass?: string
}>()
</script>

<style lang="scss" scoped>
.kv-card {
	border: 1px solid var(--border-color);
	background-color: var(--bg-secondary-color);
	border-radius: var(--border-radius);
	overflow: hidden;
	display: flex;
	flex-direction: column;

	.key {
		border-bottom: 1px solid var(--border-color);
		padding: 8px 12px;
		font-size: 12px;
	}
	.value {
		font-size: 14px;
		padding: 8px 12px;
		background-color: var(--bg-default-color);
		font-family: var(--font-family-mono);
		height: 100%;
		flex-grow: 1;
		word-break: break-word;
	}

	&.kv-size- {
		&lg {
			.key {
				padding: 10px 12px;
				font-size: 14px;
			}
			.value {
				font-size: 16px;
				padding: 12px 12px;
			}
		}
	}

	&.kv-color- {
		&danger {
			border-color: rgba(var(--error-color-rgb) / 0.3);
			background-color: rgba(var(--error-color-rgb) / 0.2);

			.key {
				border-color: rgba(var(--error-color-rgb) / 0.3);
			}
		}

		&warning {
			border-color: rgba(var(--warning-color-rgb) / 0.3);
			background-color: rgba(var(--warning-color-rgb) / 0.2);

			.key {
				border-color: rgba(var(--warning-color-rgb) / 0.3);
			}
		}

		&success {
			border-color: rgba(var(--success-color-rgb), 0.3);
			background-color: rgba(var(--success-color-rgb), 0.2);

			.key {
				border-color: rgba(var(--success-color-rgb), 0.3);
			}
		}

		&primary {
			border-color: rgba(var(--primary-color-rgb) / 0.3);
			background-color: rgba(var(--primary-color-rgb) / 0.2);

			.key {
				border-color: rgba(var(--primary-color-rgb) / 0.3);
			}
		}
	}
}
</style>
