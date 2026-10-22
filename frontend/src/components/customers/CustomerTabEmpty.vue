<template>
	<!--
		A customer tab with nothing configured yet: what the feature is, what setting it up gives,
		and the action that starts it, instead of a lone button in an empty pane.
	-->
	<section
		class="customer-tab-empty border-default bg-default @container relative overflow-hidden rounded-xl border"
		data-testid="customer-tab-empty"
	>
		<div class="relative grid gap-0 @3xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
			<div class="flex flex-col gap-4 p-6 @3xl:p-8">
				<div class="flex items-center gap-3">
					<span
						class="border-default bg-secondary text-primary flex size-10 shrink-0 items-center justify-center rounded-lg border"
					>
						<Icon :name="icon" :size="20" />
					</span>
					<span
						class="text-tertiary font-mono text-[10px] tracking-[0.14em] uppercase"
						data-testid="customer-tab-empty-eyebrow"
					>
						{{ eyebrow }}
					</span>
				</div>
				<div class="flex flex-col gap-2">
					<h3
						class="font-display text-default m-0 text-lg leading-snug font-semibold text-balance"
						data-testid="customer-tab-empty-title"
					>
						{{ title }}
					</h3>
					<p class="text-secondary m-0 max-w-prose text-sm leading-relaxed text-pretty">
						{{ description }}
					</p>
				</div>
				<div v-if="$slots.actions" class="flex flex-wrap items-center gap-2 pt-1" data-testid="customer-tab-empty-actions">
					<slot name="actions" />
				</div>
				<p v-if="note" class="text-tertiary m-0 text-xs leading-relaxed">{{ note }}</p>
			</div>

			<div
				v-if="points.length"
				class="border-default bg-secondary/60 flex flex-col border-t p-6 @3xl:border-t-0 @3xl:border-l @3xl:p-8"
			>
				<span class="text-tertiary mb-3 font-mono text-[10px] tracking-[0.14em] uppercase">{{ pointsTitle }}</span>
				<ol class="m-0 flex list-none flex-col p-0" data-testid="customer-tab-empty-points">
					<li
						v-for="(point, index) of points"
						:key="point.title"
						class="border-default flex gap-3 border-t py-3 first:border-t-0 first:pt-0 last:pb-0"
					>
						<span class="text-primary w-6 shrink-0 pt-px font-mono text-xs tabular-nums">
							{{ String(index + 1).padStart(2, "0") }}
						</span>
						<span class="flex min-w-0 flex-col gap-0.5">
							<span class="text-default text-sm font-medium">{{ point.title }}</span>
							<span class="text-secondary text-xs leading-relaxed">{{ point.description }}</span>
						</span>
					</li>
				</ol>
			</div>
		</div>
	</section>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"

export interface EmptyPoint {
	title: string
	description: string
}

const {
	icon,
	title,
	description,
	eyebrow = "Not set up",
	points = [],
	pointsTitle = "What it sets up",
	note
} = defineProps<{
	icon: string
	title: string
	description: string
	eyebrow?: string
	points?: EmptyPoint[]
	pointsTitle?: string
	note?: string
}>()
</script>

<style scoped>
/* A faint dot grid behind the panel: texture, not decoration that competes with the copy. */
.customer-tab-empty::before {
	content: "";
	position: absolute;
	inset: 0;
	pointer-events: none;
	background-image: radial-gradient(var(--border-color) 1px, transparent 1px);
	background-size: 16px 16px;
	mask-image: linear-gradient(to bottom right, rgb(0 0 0 / 0.55), transparent 60%);
	opacity: 0.6;
}
</style>
