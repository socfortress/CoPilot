<template>
	<div class="activity-list" role="list">
		<template v-if="loading">
			<ActivityListItemSkeleton
				v-for="(shape, index) of skeletonShapes"
				:key="index"
				v-bind="shape"
				:with-action="skeletonAction"
			/>
		</template>

		<template v-else>
			<ActivityListItem v-for="item of items" :key="item.id" :item>
				<template v-if="$slots.action" #action="{ item: row }">
					<slot name="action" :item="row" />
				</template>
			</ActivityListItem>
		</template>
	</div>
</template>

<script setup lang="ts">
import type { ActivityItem, ActivitySkeletonShape } from "./types"
import { computed } from "vue"
import ActivityListItem from "./ActivityListItem.vue"
import ActivityListItemSkeleton from "./ActivityListItemSkeleton.vue"

const {
	items = [],
	skeletonRows = 4,
	skeletonDetailLines = [0],
	skeletonAction = true
} = defineProps<{
	items?: ActivityItem[]
	/** Render placeholder rows instead of `items`. */
	loading?: boolean
	skeletonRows?: number
	/** Detail lines per placeholder row, cycled — mirror what the feed usually shows. */
	skeletonDetailLines?: number[]
	skeletonAction?: boolean
}>()

defineSlots<{
	action?: (props: { item: ActivityItem }) => unknown
}>()

// Slightly uneven widths: a column of identical bars reads as a table, not a feed.
const TITLE_WIDTHS = ["72%", "58%", "66%", "49%", "61%", "54%"]
const META_WIDTHS = ["38%", "30%", "44%", "26%", "34%", "40%"]

const skeletonShapes = computed<ActivitySkeletonShape[]>(() =>
	Array.from({ length: skeletonRows }, (_, index) => ({
		titleWidth: TITLE_WIDTHS[index % TITLE_WIDTHS.length],
		metaWidth: META_WIDTHS[index % META_WIDTHS.length],
		detailLines: skeletonDetailLines[index % skeletonDetailLines.length] ?? 0
	}))
)
</script>

<style lang="scss" scoped>
.activity-list {
	// Rows adapt to the list's width, not the viewport's (see ActivityRow).
	container: activity-list / inline-size;
	min-width: 0;
}
</style>
