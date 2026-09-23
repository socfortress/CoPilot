<template>
	<section class="bg-default border-default flex min-w-0 flex-col rounded-lg border">
		<header class="border-default flex items-center justify-between gap-3 border-b px-5 py-3.5">
			<div class="flex min-w-0 items-center gap-2.5">
				<Icon v-if="icon" :name="icon" :size="16" class="text-secondary shrink-0" />
				<h2 class="truncate text-sm font-semibold">{{ title }}</h2>
				<span v-if="meta" class="text-tertiary font-mono text-xs tabular-nums">{{ meta }}</span>
			</div>

			<RouterLink
				v-if="link"
				:to="link.to"
				class="text-secondary hover:text-primary focus-visible:text-primary focus-visible:outline-primary flex shrink-0 items-center gap-1 rounded text-xs font-medium no-underline transition-colors focus-visible:outline-2 focus-visible:outline-offset-2"
			>
				{{ link.label }}
				<Icon name="carbon:arrow-right" :size="14" />
			</RouterLink>
		</header>

		<!--
			One state at a time. The skeleton is the caller's: only it knows what the
			loaded content looks like, which is what keeps the layout from shifting.
		-->
		<div class="flex grow flex-col" :aria-busy="loading || undefined">
			<slot v-if="loading" name="skeleton" />
			<PanelError v-else-if="error" :message="error" @retry="emit('retry')" />
			<PanelEmpty v-else-if="empty" :text="emptyText" />
			<slot v-else />
		</div>
	</section>
</template>

<script setup lang="ts">
import type { RouteLocationRaw } from "vue-router"
import { RouterLink } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import PanelEmpty from "./PanelEmpty.vue"
import PanelError from "./PanelError.vue"

const { emptyText = "Nothing to show" } = defineProps<{
	title: string
	icon?: string
	/** Short muted text after the title, e.g. "latest 6". */
	meta?: string
	/** Header link to the full list. */
	link?: { to: RouteLocationRaw; label: string }
	loading?: boolean
	error?: string | null
	empty?: boolean
	emptyText?: string
}>()

const emit = defineEmits<{
	(e: "retry"): void
}>()
</script>
