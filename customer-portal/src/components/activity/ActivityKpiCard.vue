<template>
	<article
		class="bg-default border-default flex min-w-0 flex-col gap-3 rounded-lg border p-4"
		:data-testid="`activity-kpi-${kpi.key}`"
	>
		<header class="flex items-center justify-between gap-2">
			<h3 class="text-secondary text-sm font-medium">{{ kpi.title }}</h3>
			<span
				v-if="kpi.delta"
				class="text-secondary flex items-center gap-0.5 font-mono text-xs tabular-nums"
				:title="kpi.deltaTitle"
				data-testid="activity-kpi-delta"
			>
				<Icon v-if="kpi.delta.direction === 'up'" name="carbon:arrow-up" :size="12" />
				<Icon v-else-if="kpi.delta.direction === 'down'" name="carbon:arrow-down" :size="12" />
				<Icon v-else name="carbon:subtract" :size="12" />
				{{ kpi.delta.text }}
			</span>
		</header>

		<component
			:is="link ? RouterLink : 'span'"
			:to="link ?? undefined"
			class="font-display text-default w-fit text-3xl leading-none font-semibold tabular-nums no-underline"
			:class="{
				'hover:text-primary focus-visible:outline-primary rounded transition-colors focus-visible:outline-2 focus-visible:outline-offset-2':
					!!link
			}"
			data-testid="activity-kpi-value"
		>
			{{ kpi.value }}
		</component>

		<p class="text-tertiary font-mono text-xs tabular-nums" data-testid="activity-kpi-caption">{{ kpi.caption }}</p>
	</article>
</template>

<script setup lang="ts">
import type { RouteLocationRaw } from "vue-router"
import type { ActivityKpi } from "./activity"
import { RouterLink } from "vue-router"
import Icon from "@/components/common/Icon.vue"

defineProps<{
	kpi: ActivityKpi
	/** The list behind the figure, when it has one. */
	link?: RouteLocationRaw | null
}>()
</script>
