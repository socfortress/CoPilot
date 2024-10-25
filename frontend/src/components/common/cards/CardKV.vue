<template>
	<div class="kv-card" :class="[`kv-color-${color}`, `kv-size-${size}`]">
		<div v-if="$slots.key" class="key">
			<slot name="key"></slot>
		</div>
		<div v-if="$slots.value" class="value">
			<slot name="value"></slot>
		</div>
	</div>
</template>

<script setup lang="ts">
const { color } = defineProps<{
	color?: "danger" | "warning" | "success" | "primary"
	size?: "lg"
}>()
</script>

<style lang="scss" scoped>
.kv-card {
	border: var(--border-small-100);
	background-color: var(--bg-secondary-color);
	border-radius: var(--border-radius);
	overflow: hidden;
	display: flex;
	flex-direction: column;

	.key {
		border-bottom: var(--border-small-050);
		padding: 8px 12px;
		font-size: 12px;
	}
	.value {
		font-size: 14px;
		padding: 8px 12px;
		background-color: var(--bg-color);
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
			border-color: var(--secondary4-opacity-030-color);
			background-color: var(--secondary4-opacity-020-color);

			.key {
				border-color: var(--secondary4-opacity-030-color);
			}
		}

		&warning {
			border-color: var(--secondary3-opacity-030-color);
			background-color: var(--secondary3-opacity-020-color);

			.key {
				border-color: var(--secondary3-opacity-030-color);
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
			border-color: var(--primary-030-color);
			background-color: var(--primary-020-color);

			.key {
				border-color: var(--primary-030-color);
			}
		}
	}
}
</style>
