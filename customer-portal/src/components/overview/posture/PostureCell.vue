<template>
	<RouterLink
		:to="{ name: cell.route }"
		class="group hover:bg-hover focus-visible:outline-primary flex min-w-0 flex-col gap-4 p-5 text-inherit no-underline transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 motion-reduce:transition-none"
	>
		<div class="flex items-center justify-between gap-2">
			<span class="text-secondary flex items-center gap-2 text-sm font-medium">
				<Icon :name="cell.icon" :size="16" />
				{{ cell.title }}
			</span>
			<Icon
				name="carbon:arrow-up-right"
				:size="14"
				class="text-tertiary opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100 motion-reduce:transition-none"
			/>
		</div>

		<p v-if="error" class="text-error text-sm">{{ error }}</p>

		<PostureCellSkeleton v-else-if="loading" />

		<template v-else>
			<div class="flex items-baseline gap-2">
				<span class="font-mono text-4xl leading-none font-semibold tracking-tight tabular-nums">
					{{ cell.headline }}
				</span>
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
