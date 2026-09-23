<template>
	<ActivityRow :rail-class="bgClass(item.status.color)">
		<!-- Line heights are mirrored by ActivityListItemSkeleton: change one, change both. -->
		<p class="text-default truncate text-sm font-medium">{{ item.title }}</p>

		<p
			v-if="item.detail"
			class="text-secondary text-xs leading-normal"
			:class="item.detailLines === 2 ? 'line-clamp-2' : 'line-clamp-1'"
		>
			{{ item.detail }}
		</p>

		<p class="flex min-w-0 items-center gap-2 font-mono text-xs leading-4 tracking-wide">
			<span class="shrink-0" :class="textClass(item.status.color)">{{ item.status.label }}</span>
			<span v-if="item.meta.length" class="text-tertiary truncate">{{ item.meta.join(" · ") }}</span>
		</p>

		<template #aside>
			<RelativeTime :time="item.time" />
			<slot name="action" :item />
		</template>
	</ActivityRow>
</template>

<script setup lang="ts">
import type { ActivityItem } from "./types"
import RelativeTime from "../shared/RelativeTime.vue"
import { bgClass, textClass } from "../shared/status"
import ActivityRow from "./ActivityRow.vue"

defineProps<{
	item: ActivityItem
}>()

defineSlots<{
	/** Per-row action, e.g. the details button. */
	action?: (props: { item: ActivityItem }) => unknown
}>()
</script>
