<template>
	<ActivityRow :rail-color="colorVar(item.status.color)">
		<p class="activity-item__title">{{ item.title }}</p>

		<p
			v-if="item.detail"
			class="activity-item__detail"
			:class="item.detailLines === 2 ? 'line-clamp-2' : 'line-clamp-1'"
		>
			{{ item.detail }}
		</p>

		<p class="activity-item__meta">
			<span class="shrink-0" :style="{ color: colorVar(item.status.color) }">{{ item.status.label }}</span>
			<span v-if="item.meta.length" class="text-tertiary truncate">{{ item.meta.join(" · ") }}</span>
		</p>

		<template #aside>
			<RelativeTime :time="item.time" />
			<div v-if="$slots.action" class="activity-item__action">
				<slot name="action" :item />
			</div>
		</template>
	</ActivityRow>
</template>

<script setup lang="ts">
import type { ActivityItem } from "./types"
import RelativeTime from "../shared/RelativeTime.vue"
import { colorVar } from "../shared/status"
import ActivityRow from "./ActivityRow.vue"

defineProps<{
	item: ActivityItem
}>()

defineSlots<{
	/** Per-row action, e.g. the details button. */
	action?: (props: { item: ActivityItem }) => unknown
}>()
</script>

<style lang="scss" scoped>
// Line boxes here are mirrored by ActivityListItemSkeleton: change one, change both.
.activity-item {
	&__title {
		overflow: hidden;
		font-size: 14px;
		font-weight: 500;
		line-height: 1.35;
		white-space: nowrap;
		text-overflow: ellipsis;
		color: var(--fg-default-color);
	}

	&__detail {
		font-size: 12px;
		line-height: 1.5;
		color: var(--fg-secondary-color);
	}

	&__meta {
		display: flex;
		min-width: 0;
		align-items: center;
		gap: 8px;
		font-family: var(--font-family-mono);
		font-size: 12px;
		line-height: 16px;
		letter-spacing: 0.02em;
	}

	&__action {
		// The details buttons wrap an inline-flex group in a plain div, which would sit
		// in a 1.6 line box and add ~4px under the 22px button. As a flex container it
		// is exactly button-high and lines up with the meta line.
		> :deep(div) {
			display: flex;
		}

		// Transparent so the button sits on the row surface instead of a filled box.
		:deep(.n-button) {
			--n-color: transparent !important;
		}
	}
}
</style>
