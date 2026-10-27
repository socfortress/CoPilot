<template>
	<div class="flex flex-col gap-3">
		<div v-for="group of groups" :key="group.title" class="flex flex-col gap-1" data-testid="talon-ops-evidence-bars">
			<h5 class="text-secondary text-xs font-semibold">{{ group.title }}</h5>
			<ul class="flex flex-col gap-1" :aria-label="group.title">
				<li
					v-for="bar of group.bars"
					:key="bar.label"
					class="grid grid-cols-[minmax(0,10rem)_1fr_max-content] items-center gap-2 text-xs"
					data-testid="talon-ops-evidence-bar"
				>
					<span class="truncate font-mono" :title="bar.label"><bdi>{{ bar.label }}</bdi></span>
					<span class="bg-secondary block h-2.5 overflow-hidden rounded-sm" aria-hidden="true">
						<span
							class="block h-full rounded-r"
							:style="{ width: `${Math.max(bar.width, bar.value > 0 ? 1 : 0)}%`, backgroundColor: primary }"
						/>
					</span>
					<span class="text-right font-mono tabular-nums">{{ bar.text }}</span>
				</li>
			</ul>
		</div>
	</div>
</template>

<script setup lang="ts">
// Horizontal bars in plain HTML: a label, a bar scaled to the group's largest value, and the value as
// text beside it (so the numbers are there without the bar, for a screen reader too). One hue, the
// theme's mode-stepped data colour, so it reads in light and dark mode.
import type { BarGroup } from "./evidence"
import { useSocChartColors } from "@/components/socManagement/charts/chart-colors"

const { groups } = defineProps<{ groups: BarGroup[] }>()
const { primary } = useSocChartColors()
</script>
