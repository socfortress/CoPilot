<template>
	<section
		class="bg-default flex flex-col overflow-hidden rounded-lg border border-[rgba(var(--warning-color-rgb)/0.35)]"
	>
		<header class="border-default flex flex-wrap items-center gap-2 border-b bg-[rgba(var(--warning-color-rgb)/0.08)] px-3 py-2.25">
			<Icon :name="AlertIcon" :size="15" class="text-warning shrink-0" />
			<h4 class="text-xs font-semibold tracking-[0.02em]">Threshold simulation</h4>
			<code class="text-warning text-2xs ms-auto rounded-sm bg-[rgba(var(--warning-color-rgb)/0.12)] px-2 py-0.5 font-mono">
				{{ aggregation.function }}{{ aggregation.field ? `(${aggregation.field})` : "()" }}
				{{ aggregation.condition }} {{ aggregation.threshold }} / {{ aggregation.window }}
				<template v-if="aggregation.group_by.length">by {{ aggregation.group_by.join(", ") }}</template>
			</code>
		</header>

		<div class="flex flex-col gap-5 p-3">
			<!-- verdict figures -->
			<div class="flex flex-wrap gap-2.5">
				<div class="border-default bg-secondary flex min-w-38 flex-1 flex-col gap-0.25 rounded-sm border px-3 py-2.5">
					<span class="text-secondary text-3xs font-semibold tracking-[0.06em] uppercase">
						Would have fired
					</span>
					<span class="text-warning font-display text-[26px] leading-tight font-bold">
						≈ {{ fmt(aggregation.estimated_alerts) }}
					</span>
					<span class="text-secondary text-2xs">
						alert{{ aggregation.estimated_alerts === 1 ? "" : "s" }} in {{ rangeLabel }}
					</span>
				</div>
				<div class="border-default bg-secondary flex min-w-38 flex-1 flex-col gap-0.25 rounded-sm border px-3 py-2.5">
					<span class="text-secondary text-3xs font-semibold tracking-[0.06em] uppercase">Per day</span>
					<span class="font-display text-[26px] leading-tight font-bold">
						{{ aggregation.per_day_alerts }}
					</span>
					<span class="text-secondary text-2xs">on average</span>
				</div>
			</div>

			<div v-if="aggregation.top_offenders.length" class="flex flex-col gap-1.75">
				<SectionHeading tag="h5" accent="warning">Top offenders</SectionHeading>
				<div class="flex flex-col gap-1.5">
					<MeterRow
						v-for="(offender, i) of aggregation.top_offenders"
						:key="i"
						wide
						accent="warning"
						:label="offender.group"
						:value="offender.windows_alerting"
						:max="maxOffenderWindows"
					>
						peak <b>{{ offender.peak }}</b>
						<span class="opacity-40">·</span>
						{{ offender.windows_alerting }}×
					</MeterRow>
				</div>
			</div>

			<div v-if="aggregation.sensitivity.length" class="flex flex-col gap-1.75">
				<SectionHeading tag="h5" accent="warning">Threshold sensitivity</SectionHeading>
				<div class="flex flex-wrap gap-2">
					<div
						v-for="(step, i) of aggregation.sensitivity"
						:key="i"
						class="flex min-w-17 flex-col items-center gap-0.25 rounded-sm border px-2.5 py-1.5 transition-colors"
						:class="
							step.threshold === aggregation.threshold
								? 'border-primary bg-[rgba(var(--primary-color-rgb)/0.1)]'
								: 'border-default'
						"
					>
						<span class="text-secondary text-3xs font-mono">≥ {{ step.threshold }}</span>
						<span class="font-display text-base font-bold">{{ fmt(step.alerts) }}</span>
					</div>
				</div>
				<span class="text-secondary text-2xs">
					Alerts at each threshold — the highlighted one is the rule's current setting.
				</span>
			</div>
		</div>
	</section>
</template>

<script setup lang="ts">
import type { BacktestAggregation } from "@/types/copilot-searches"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import SectionHeading from "@/components/copilotSearches/SectionHeading.vue"
import { fmt } from "./format"
import MeterRow from "./MeterRow.vue"

const { aggregation, rangeLabel } = defineProps<{
	aggregation: BacktestAggregation
	/** Human look-back ("7d") for the "alerts in …" caption. */
	rangeLabel: string
}>()

const AlertIcon = "carbon:warning-alt"

const maxOffenderWindows = computed(() => Math.max(1, ...aggregation.top_offenders.map(o => o.windows_alerting)))
</script>
