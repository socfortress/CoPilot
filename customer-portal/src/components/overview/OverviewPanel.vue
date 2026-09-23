<template>
	<section class="overview-panel bg-default border-default flex min-w-0 flex-col rounded-lg border">
		<header class="border-default flex items-center justify-between gap-3 border-b px-5 py-3.5">
			<div class="flex min-w-0 items-center gap-2.5">
				<Icon v-if="icon" :name="icon" :size="16" class="text-secondary shrink-0" />
				<h2 class="truncate text-sm font-semibold">{{ title }}</h2>
				<span v-if="meta" class="text-tertiary font-mono text-xs tabular-nums">{{ meta }}</span>
			</div>
			<slot name="header-extra">
				<RouterLink
					v-if="to"
					:to
					class="view-all text-secondary flex shrink-0 items-center gap-1 text-xs font-medium"
				>
					{{ linkLabel }}
					<Icon name="carbon:arrow-right" :size="14" />
				</RouterLink>
			</slot>
		</header>

		<div class="flex grow flex-col">
			<template v-if="loading">
				<slot name="skeleton">
					<div class="flex flex-col gap-4 p-5" aria-busy="true">
						<div v-for="n of skeletonRows" :key="n" class="flex items-center gap-3">
							<n-skeleton :width="8" :height="8" circle />
							<div class="flex grow flex-col gap-2">
								<n-skeleton :height="12" :width="`${60 + ((n * 17) % 30)}%`" :sharp="false" />
								<n-skeleton :height="10" :width="`${30 + ((n * 11) % 20)}%`" :sharp="false" />
							</div>
						</div>
					</div>
				</slot>
			</template>

			<div v-else-if="error" class="flex grow flex-col items-start gap-2 p-5">
				<p class="text-error text-sm">{{ error }}</p>
				<n-button size="small" secondary @click="emit('retry')">Try again</n-button>
			</div>

			<div v-else-if="empty" class="flex grow flex-col items-center justify-center gap-1 p-8 text-center">
				<Icon name="carbon:checkmark-outline" :size="20" class="text-tertiary" />
				<p class="text-secondary text-sm">{{ emptyText }}</p>
			</div>

			<slot v-else />
		</div>
	</section>
</template>

<script setup lang="ts">
import type { RouteLocationRaw } from "vue-router"
import { NButton, NSkeleton } from "naive-ui"
import { RouterLink } from "vue-router"
import Icon from "@/components/common/Icon.vue"

const {
	skeletonRows = 4,
	linkLabel = "View all",
	emptyText = "Nothing to show"
} = defineProps<{
	title: string
	icon?: string
	meta?: string
	to?: RouteLocationRaw
	linkLabel?: string
	loading?: boolean
	error?: string | null
	empty?: boolean
	emptyText?: string
	skeletonRows?: number
}>()

const emit = defineEmits<{
	(e: "retry"): void
}>()
</script>

<style lang="scss" scoped>
.overview-panel {
	.view-all {
		text-decoration: none;
		transition: color 0.2s ease;

		&:hover,
		&:focus-visible {
			color: var(--primary-color);
		}

		&:focus-visible {
			outline: 2px solid var(--primary-color);
			outline-offset: 2px;
			border-radius: 4px;
		}
	}
}
</style>
