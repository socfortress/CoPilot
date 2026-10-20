<template>
	<div class="flex flex-col gap-6" data-testid="activity-page">
		<header class="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
			<div class="flex min-w-0 flex-col gap-1.5">
				<h1 class="font-display text-2xl leading-tight font-semibold tracking-tight text-balance">Activity</h1>
				<p class="text-secondary max-w-prose text-sm">
					What reached the SOC for you, where it came from and how it was judged, beside the period before.
				</p>
			</div>

			<n-radio-group :value="range" size="small" data-testid="activity-range" @update:value="setRange">
				<n-radio-button
					v-for="preset of RANGE_PRESETS"
					:key="preset.key"
					:value="preset.key"
					:data-testid="`activity-range-${preset.key}`"
				>
					{{ preset.label }}
				</n-radio-button>
			</n-radio-group>
		</header>

		<n-alert v-if="error && activity" type="warning" :bordered="false" data-testid="activity-refresh-error">
			Could not refresh the figures: {{ error }}
		</n-alert>

		<PanelError
			v-if="error && !activity"
			:message="error"
			class="bg-default border-default rounded-lg border"
			@retry="reload()"
		/>

		<div
			v-else-if="activity && !activity.enabled"
			class="bg-default border-default flex flex-col items-center gap-2 rounded-lg border px-6 py-14 text-center"
			data-testid="activity-disabled"
		>
			<Icon name="carbon:activity" :size="28" class="text-tertiary" />
			<p class="font-semibold">Activity is not available yet</p>
			<p class="text-secondary max-w-md text-sm">
				Your SOC has not published the activity breakdown for this customer. Ask your SOC contact if you would
				like to see it here.
			</p>
		</div>

		<template v-else>
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4" :aria-busy="loading || undefined">
				<template v-if="activity">
					<ActivityKpiCard
						v-for="kpi of kpis"
						:key="kpi.key"
						:kpi
						:link="kpi.key === 'alerts' ? alertsLink(activity, 'current', null) : null"
						:class="{ 'opacity-60': loading }"
					/>
				</template>
				<template v-else>
					<n-skeleton v-for="n of 4" :key="n" height="118px" :sharp="false" class="rounded-lg" />
				</template>
			</div>

			<p v-if="activity" class="text-tertiary -mt-2 text-xs" data-testid="activity-note">
				Counted from when each alert and case reached the SOC, {{ periodText }}. Select a count to list those
				alerts.
			</p>

			<div class="grid grid-cols-1 gap-6 xl:grid-cols-2" :class="{ 'opacity-60': loading && !!activity }">
				<OverviewPanel
					v-for="panel of alertPanels"
					:key="panel.testid"
					:title="panel.title"
					:icon="panel.icon"
					:meta="periodMeta"
					:loading="!activity"
					:error="activity?.alerts.error"
					:empty="!!activity && !panel.items.length"
					:empty-text="panel.empty"
					:data-testid="`${panel.testid}-panel`"
					@retry="reload()"
				>
					<template #skeleton>
						<div class="p-5"><n-skeleton text :repeat="5" /></div>
					</template>
					<ActivityRankList :items="panel.items" :link="panel.link" :testid="panel.testid" />
					<p
						v-if="panel.testid === 'activity-severities'"
						class="text-tertiary border-default mt-auto border-t px-5 py-3 text-xs"
						data-testid="activity-severity-note"
					>
						An alert whose source sent no severity counts at the SOC's default level.
					</p>
					<p
						v-if="panel.testid === 'activity-sources' && otherSources"
						class="text-tertiary border-default mt-auto border-t px-5 py-3 font-mono text-xs tabular-nums"
						data-testid="activity-other-sources"
					>
						{{ otherSources }}
					</p>
				</OverviewPanel>

				<OverviewPanel
					title="Cases"
					icon="carbon:folder"
					:meta="periodMeta"
					:loading="!activity"
					:error="activity?.cases.error"
					:empty="!!activity && !activity.cases.opened.count && !activity.cases.opened.previous"
					empty-text="No case was opened in either period"
					data-testid="activity-cases-panel"
					@retry="reload()"
				>
					<template #skeleton>
						<div class="p-5"><n-skeleton text :repeat="5" /></div>
					</template>
					<template v-if="activity">
						<h3 class="text-secondary px-5 pt-4 text-xs font-medium">By type</h3>
						<ActivityRankList :items="activity.cases.by_type" testid="activity-case-types" />
						<h3 class="text-secondary border-default border-t px-5 pt-4 text-xs font-medium">
							Where the cases opened stand now
						</h3>
						<ActivityRankList
							:items="activity.cases.by_status"
							label-kind="status"
							testid="activity-case-statuses"
						/>
					</template>
				</OverviewPanel>
				<OverviewPanel
					title="The SOC's verdicts"
					icon="carbon:result"
					:meta="periodMeta"
					:loading="!activity"
					:error="activity?.verdicts.error"
					:empty="!!activity && !activity.verdicts.current.total"
					empty-text="No alerts this period"
					class="xl:col-span-2"
					data-testid="activity-verdicts-panel"
					@retry="reload()"
				>
					<template #skeleton>
						<div class="p-5"><n-skeleton text :repeat="5" /></div>
					</template>
					<template v-if="activity">
						<dl
							class="border-default grid grid-cols-3 gap-px border-b font-mono text-xs tabular-nums"
							data-testid="activity-verdict-split"
						>
							<div v-for="part of verdictSplit" :key="part.key" class="flex flex-col gap-1 px-5 py-3">
								<dt class="text-tertiary font-sans">{{ part.label }}</dt>
								<dd class="text-default text-lg font-semibold">{{ part.value }}</dd>
							</div>
						</dl>
						<!-- Side by side when the panel spans the page: why, and where from. -->
						<div class="divide-default grid grid-cols-1 lg:grid-cols-2 lg:divide-x">
							<section>
								<h3 class="text-secondary px-5 pt-4 text-xs font-medium">
									Why alerts were false positives
								</h3>
								<ActivityRankList
									v-if="activity.verdicts.reasons.length"
									:items="activity.verdicts.reasons"
									testid="activity-reasons"
								/>
								<p v-else class="text-tertiary px-5 py-4 text-xs">No false positive this period.</p>
							</section>
							<section>
								<h3 class="text-secondary px-5 pt-4 text-xs font-medium">
									Detections with the most false positives
								</h3>
								<ul
									v-if="activity.verdicts.noisy_detections.length"
									class="flex flex-col gap-3 px-5 py-4"
									data-testid="activity-noisy"
								>
									<li
										v-for="noisy of activity.verdicts.noisy_detections"
										:key="noisy.name"
										class="flex items-baseline justify-between gap-3 text-sm"
									>
										<bdi class="min-w-0 truncate" :title="noisy.name">{{ noisy.name }}</bdi>
										<span class="text-secondary font-mono text-xs whitespace-nowrap tabular-nums">
											{{ noisy.false_positives }} of {{ noisy.reviewed }} reviewed ·
											{{ formatRate(noisy.false_positive_rate) }}
										</span>
									</li>
								</ul>
								<p v-else class="text-tertiary px-5 py-4 text-xs">No false positive this period.</p>
							</section>
						</div>
					</template>
				</OverviewPanel>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import type { RouteLocationRaw } from "vue-router"
import type { DrillKind, Period } from "./activity"
import type { ActivityCount, ActivityRange } from "@/types/activity"
import { NAlert, NRadioButton, NRadioGroup, NSkeleton } from "naive-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import OverviewPanel from "@/components/overview/shared/OverviewPanel.vue"
import PanelError from "@/components/overview/shared/PanelError.vue"
import { alertsLink, buildKpis, formatRate, RANGE_PRESETS, rangeFromQuery, rangeLabel, withRange } from "./activity"
import ActivityKpiCard from "./ActivityKpiCard.vue"
import ActivityRankList from "./ActivityRankList.vue"
import { useActivity } from "./useActivity"

const route = useRoute()
const router = useRouter()

// The range lives in the URL (`?range=7d`), the default left out: a link or a reload
// shows the same period. A change replaces the entry, like every filter in the portal.
const range = computed<ActivityRange>(() => rangeFromQuery(route.query.range))
function setRange(next: ActivityRange) {
	if (next !== range.value) router.replace({ query: withRange(route.query, next) })
}

const { activity, error, loading, reload } = useActivity(range)

const kpis = computed(() => (activity.value ? buildKpis(activity.value) : []))
const periodMeta = computed(() => `last ${rangeLabel(range.value)}`)
const periodText = computed(
	() => `over the last ${rangeLabel(range.value)} beside the ${rangeLabel(range.value)} before`
)

/** Where a slice of `kind` leads: the alerts list showing exactly what it counted. */
function drill(kind: DrillKind | null) {
	if (!kind) return undefined
	return (item: ActivityCount, period: Period): RouteLocationRaw | null =>
		activity.value ? alertsLink(activity.value, period, kind, item.key) : null
}

interface AlertPanel {
	title: string
	icon: string
	items: ActivityCount[]
	link?: (item: ActivityCount, period: Period) => RouteLocationRaw | null
	empty: string
	testid: string
}

const alertPanels = computed<AlertPanel[]>(() => {
	const alerts = activity.value?.alerts
	return [
		{
			title: "Alerts by source",
			icon: "carbon:data-base",
			items: alerts?.by_source ?? [],
			link: drill("source"),
			empty: "No alerts in either period",
			testid: "activity-sources"
		},
		{
			title: "Alerts by severity",
			icon: "carbon:warning-alt",
			items: (alerts?.by_severity ?? []).filter(item => item.count || item.previous),
			empty: "No alerts in either period",
			testid: "activity-severities"
		},
		{
			title: "Busiest detections",
			icon: "carbon:security",
			items: alerts?.top_detections ?? [],
			link: drill("detection"),
			empty: "No alerts this period",
			testid: "activity-detections"
		},
		{
			title: "Busiest assets",
			icon: "carbon:devices",
			items: alerts?.top_assets ?? [],
			link: drill("asset"),
			empty: "No alert named an asset this period",
			testid: "activity-assets"
		},
		{
			title: "Busiest tags",
			icon: "carbon:tag",
			items: alerts?.top_tags ?? [],
			link: drill("tag"),
			empty: "No tagged alert this period",
			testid: "activity-tags"
		}
	]
})

const otherSources = computed(() => {
	const other = activity.value?.alerts.other_sources
	if (!other || (!other.count && !other.previous)) return null
	return `Other sources: ${other.count} (${other.previous} the period before)`
})

const verdictSplit = computed(() => {
	const current = activity.value?.verdicts.current
	return [
		{ key: "true", label: "True positives", value: current?.true_positive ?? 0 },
		{ key: "false", label: "False positives", value: current?.false_positive ?? 0 },
		{ key: "untriaged", label: "Not reviewed yet", value: current?.untriaged ?? 0 }
	]
})
</script>
