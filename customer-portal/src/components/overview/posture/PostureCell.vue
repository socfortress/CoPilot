<template>
	<RouterLink :to="{ name: cell.route }" class="posture-cell group">
		<div class="flex items-center justify-between gap-2">
			<span class="text-secondary flex items-center gap-2 text-sm font-medium">
				<Icon :name="cell.icon" :size="16" />
				{{ cell.title }}
			</span>
			<Icon name="carbon:arrow-up-right" :size="14" class="posture-cell__arrow text-tertiary" />
		</div>

		<p v-if="error" class="text-error text-sm">{{ error }}</p>

		<PostureCellSkeleton v-else-if="loading" />

		<template v-else>
			<div class="flex items-baseline gap-2">
				<span class="posture-cell__headline">{{ cell.headline }}</span>
				<span class="text-secondary text-sm">{{ cell.caption }}</span>
			</div>

			<StatusBar :segments="cell.segments" />

			<div class="flex flex-wrap items-center justify-between gap-x-4 gap-y-1.5">
				<StatusLegend :segments="cell.segments" />
				<span class="text-tertiary font-mono text-xs tabular-nums">{{ cell.footnote }}</span>
			</div>
		</template>
	</RouterLink>
</template>

<script setup lang="ts">
import type { PostureCellModel } from "./postureCells"
import { RouterLink } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import StatusBar from "../shared/StatusBar.vue"
import StatusLegend from "../shared/StatusLegend.vue"
import PostureCellSkeleton from "./PostureCellSkeleton.vue"

defineProps<{
	cell: PostureCellModel
	loading?: boolean
	error?: string | null
}>()
</script>

<style lang="scss" scoped>
.posture-cell {
	display: flex;
	min-width: 0;
	flex-direction: column;
	gap: 16px;
	padding: 20px;
	color: inherit;
	text-decoration: none;
	transition: background-color 0.2s ease;

	&:hover {
		background-color: var(--hover-color);
	}

	&:focus-visible {
		outline: 2px solid var(--primary-color);
		outline-offset: -2px;
	}

	&__arrow {
		opacity: 0;
		transition: opacity 0.2s ease;
	}

	&:hover &__arrow,
	&:focus-visible &__arrow {
		opacity: 1;
	}

	&__headline {
		font-family: var(--font-family-mono);
		font-size: 2.125rem;
		font-weight: 600;
		line-height: 1;
		letter-spacing: -0.03em;
		font-variant-numeric: tabular-nums;
	}
}

@media (prefers-reduced-motion: reduce) {
	.posture-cell,
	.posture-cell__arrow {
		transition: none;
	}
}
</style>
