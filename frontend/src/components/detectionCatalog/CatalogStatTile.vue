<template>
	<!--
		Shared stat tile for the Detections Catalog hero strip + per-tab headers.
		Mirrors the pattern used in FeedbackMetricTile / CardStatsIcon so the
		catalog visually slots into CoPilot's existing dashboard language
		instead of inventing its own.

		Props are intentionally minimal — the catalog has many stat tiles and
		any complexity here would propagate everywhere.
	-->
	<CardEntity size="small" embedded :hoverable="!!to" :clickable="!!to" @click="onClick">
		<template #default>
			<div class="catalog-stat-tile flex items-center gap-3">
				<div v-if="icon" class="icon-wrap" :class="`accent-${accent}`">
					<Icon :name="icon" :size="18" />
				</div>
				<div class="flex grow flex-col gap-0.5 overflow-hidden">
					<div class="label text-secondary text-xs tracking-wide uppercase">
						{{ label }}
					</div>
					<div class="value flex items-baseline gap-2" :class="`accent-${accent}-value`">
						<span class="font-display text-2xl leading-none font-semibold">
							{{ formattedValue }}
						</span>
						<span v-if="suffix" class="text-tertiary text-xs">{{ suffix }}</span>
					</div>
					<div v-if="sub" class="text-tertiary truncate text-xs">{{ sub }}</div>
				</div>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import { computed } from "vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"

type Accent = "default" | "primary" | "success" | "warning" | "danger"

const props = defineProps<{
	label: string
	value: number | string
	sub?: string
	suffix?: string
	icon?: string
	accent?: Accent
	/**
	 * When set, the tile becomes clickable and emits ``navigate`` instead of
	 * navigating directly — keeps the tile presentational and lets the parent
	 * decide where the click leads (usually a tab/URL change).
	 */
	to?: string
}>()

const emit = defineEmits<{ (e: "navigate", to: string): void }>()

const accent = computed<Accent>(() => props.accent ?? "default")

// Format numbers with thousand separators; pass strings through untouched.
const formattedValue = computed(() => (typeof props.value === "number" ? props.value.toLocaleString() : props.value))

function onClick() {
	if (props.to) emit("navigate", props.to)
}
</script>

<style scoped lang="scss">
.catalog-stat-tile {
	.icon-wrap {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 36px;
		height: 36px;
		border-radius: 8px;
		flex-shrink: 0;
		background-color: rgba(var(--border-color-rgb) / 0.15);
		color: var(--fg-secondary-color);
		transition: all 0.2s var(--bezier-ease);

		&.accent-primary {
			background-color: rgba(var(--primary-color-rgb) / 0.1);
			color: var(--primary-color);
		}
		&.accent-success {
			background-color: rgba(var(--success-color-rgb) / 0.1);
			color: var(--success-color);
		}
		&.accent-warning {
			background-color: rgba(var(--warning-color-rgb) / 0.12);
			color: var(--warning-color);
		}
		&.accent-danger {
			background-color: rgba(var(--error-color-rgb) / 0.1);
			color: var(--error-color);
		}
	}

	.value {
		font-family: var(--font-family-display);

		&.accent-primary-value {
			color: var(--primary-color);
		}
		&.accent-success-value {
			color: var(--success-color);
		}
		&.accent-warning-value {
			color: var(--warning-color);
		}
		&.accent-danger-value {
			color: var(--error-color);
		}
	}
}
</style>
