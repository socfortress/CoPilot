<template>
	<div class="flex flex-col gap-6" data-testid="sla-page">
		<header class="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
			<div class="flex min-w-0 flex-col gap-1.5">
				<h1 class="font-display text-2xl leading-tight font-semibold tracking-tight text-balance">Service levels</h1>
				<p class="text-secondary text-sm">
					How fast the SOC answered and resolved your alerts and cases, against the targets agreed with you.
				</p>
			</div>

			<div class="flex items-center gap-3">
				<span v-if="trackingNote" class="text-tertiary font-mono text-xs" data-testid="sla-tracking-since">
					{{ trackingNote }}
				</span>
				<n-radio-group v-model:value="period" size="small" data-testid="sla-period">
					<n-radio-button
						v-for="preset of PERIOD_PRESETS"
						:key="preset.key"
						:value="preset.key"
						:data-testid="`sla-period-${preset.key}`"
					>
						{{ preset.label }}
					</n-radio-button>
				</n-radio-group>
			</div>
		</header>

		<n-alert v-if="error && overview" type="warning" :bordered="false" data-testid="sla-refresh-error">
			Could not refresh the figures: {{ error }}
		</n-alert>

		<PanelError v-if="error && !overview" :message="error" class="bg-default border-default rounded-lg border" @retry="reload()" />

		<div
			v-else-if="overview && !overview.enabled"
			class="bg-default border-default flex flex-col items-center gap-2 rounded-lg border px-6 py-14 text-center"
			data-testid="sla-disabled"
		>
			<Icon name="carbon:meter" :size="28" class="text-tertiary" />
			<p class="font-semibold">Service levels are not available yet</p>
			<p class="text-secondary max-w-md text-sm">
				Your SOC has not published service level figures for this customer. Ask your SOC contact if you would like
				to see them here.
			</p>
		</div>

		<template v-else>
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4" :aria-busy="loading || undefined">
				<template v-if="overview">
					<SlaKpiCard v-for="kpi of kpis" :key="kpi.key" :kpi :class="{ 'opacity-60': loading }" />
				</template>
				<template v-else>
					<n-skeleton v-for="n of 4" :key="n" height="132px" :sharp="false" class="rounded-lg" />
				</template>
			</div>

			<SlaOpenNow v-if="overview?.open_now" :open-now="overview.open_now" />

			<div class="grid grid-cols-1 gap-6 xl:grid-cols-5">
				<OverviewPanel
					title="Resolved within target"
					icon="carbon:chart-line"
					:meta="periodMeta"
					:loading="!overview"
					:empty="!!overview && !active"
					empty-text="Nothing tracked was opened or resolved in this period"
					class="xl:col-span-3"
					data-testid="sla-trend"
				>
					<template #skeleton>
						<div class="p-5"><n-skeleton height="260px" :sharp="false" /></div>
					</template>
					<div class="px-3 pt-2 pb-3">
						<SlaTrendChart v-if="overview" :points="overview.trend" :bucket="overview.bucket" />
					</div>
				</OverviewPanel>

				<OverviewPanel
					title="Our commitment"
					icon="carbon:certificate-check"
					:loading="!overview"
					:empty="!!overview && !targetGroups.length"
					empty-text="No targets apply to your alerts and cases"
					class="xl:col-span-2"
				>
					<template #skeleton>
						<div class="p-5"><n-skeleton text :repeat="6" /></div>
					</template>
					<SlaTargetsTable :groups="targetGroups" />
				</OverviewPanel>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import type { PeriodPreset } from "./sla"
import { NAlert, NRadioButton, NRadioGroup, NSkeleton } from "naive-ui"
import { computed, ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import OverviewPanel from "@/components/overview/shared/OverviewPanel.vue"
import PanelError from "@/components/overview/shared/PanelError.vue"
import { buildKpis, DEFAULT_PERIOD, groupTargets, hasActivity, PERIOD_PRESETS } from "./sla"
import SlaKpiCard from "./SlaKpiCard.vue"
import SlaOpenNow from "./SlaOpenNow.vue"
import SlaTargetsTable from "./SlaTargetsTable.vue"
import SlaTrendChart from "./SlaTrendChart.vue"
import { useSlaOverview } from "./useSlaOverview"

const period = ref<PeriodPreset["key"]>(DEFAULT_PERIOD)
const { overview, error, loading, reload } = useSlaOverview(period)

const kpis = computed(() => (overview.value ? buildKpis(overview.value) : []))
const active = computed(() => !!overview.value && hasActivity(overview.value))
const targetGroups = computed(() => groupTargets(overview.value?.targets ?? []))
const periodMeta = computed(() => `last ${PERIOD_PRESETS.find(preset => preset.key === period.value)?.label}`)

// Items from before the SOC started measuring count in no figure: say when that was,
// when it falls inside the period shown.
const trackingNote = computed(() => {
	const since = overview.value?.tracking_since
	const from = overview.value?.date_from
	if (!since || !from || new Date(since) <= new Date(from)) return null
	return `measured since ${new Date(since).toLocaleDateString(undefined, { month: "short", day: "numeric" })}`
})
</script>
