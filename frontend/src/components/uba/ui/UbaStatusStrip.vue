<template>
	<section
		class="status-strip border-default divide-border grid grid-cols-2 divide-y overflow-hidden rounded-lg border @3xl:divide-x @3xl:divide-y-0"
		:style="{ '--cells': cells.length }"
		aria-label="UBA status for this customer"
		data-testid="uba-status-strip"
	>
		<n-tooltip v-for="cell of cells" :key="cell.key" :disabled="!cell.title" placement="bottom" style="max-width: 320px">
			<template #trigger>
				<div
					class="cell border-border flex min-w-0 flex-col gap-1.5 px-4 py-3 @max-3xl:odd:border-l"
					:class="{ 'is-warn': cell.tone === 'warning', 'is-bad': cell.tone === 'error' }"
					:data-testid="`uba-status-${cell.key}`"
				>
					<span class="text-tertiary flex min-w-0 items-center gap-1.5 text-xs whitespace-nowrap">
						<Icon :name="cell.icon" :size="13" class="shrink-0" :class="toneText(cell.tone)" />
						<span class="truncate">{{ cell.label }}</span>
					</span>
					<span
						class="truncate font-mono text-xl leading-none font-semibold tabular-nums"
						:class="toneText(cell.tone)"
						data-testid="uba-status-value"
					>
						{{ cell.value }}
					</span>
				</div>
			</template>
			<span class="text-xs whitespace-pre-line">{{ cell.title }}</span>
		</n-tooltip>
	</section>
</template>

<script setup lang="ts">
// The customer's UBA at a glance, one strip split by hairlines (the shape of the Customer Portal's
// status strip): open alerts, the last day's alerts and findings, how far behind processing is,
// each data feed and the computers reporting. A cell turns amber or red only when it needs a look;
// its tooltip says why.
import type { UbaTenantStatus } from "@/types/uba"
import { NTooltip } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { agentsSummaryTitle, formatLag } from "../utils"

type Tone = "neutral" | "warning" | "error"

interface Cell {
	key: string
	label: string
	icon: string
	value: string
	tone: Tone
	title?: string
}

const { status } = defineProps<{ status: UbaTenantStatus }>()

const FEED_LABELS: Record<string, string> = { office365: "Microsoft 365", wazuh: "Wazuh" }

const cells = computed<Cell[]>(() => {
	const list: Cell[] = [
		{
			key: "open-alerts",
			label: "Open alerts",
			icon: "carbon:warning-alt",
			value: String(status.open_alerts),
			tone: status.open_alerts ? "error" : "neutral"
		},
		{ key: "alerts-24h", label: "Alerts 24 h", icon: "carbon:notification", value: String(status.alerts_24h), tone: "neutral" },
		{ key: "signals-24h", label: "Findings 24 h", icon: "carbon:activity", value: String(status.signals_24h), tone: "neutral" },
		{
			key: "lag",
			label: "Processing lag",
			icon: "carbon:time",
			value: formatLag(status.lag_seconds),
			tone: (status.lag_seconds ?? 0) > 600 ? "warning" : "neutral",
			title: "How far behind real time UBA's processing is."
		}
	]
	for (const feed of status.feeds ?? []) {
		list.push({
			key: `feed-${feed.source}`,
			label: FEED_LABELS[feed.source] ?? feed.source,
			icon: "carbon:data-base",
			value: feed.status === "ok" ? formatLag(feed.lag_p50_s) : feed.status,
			tone: feed.status === "ok" ? "neutral" : "warning",
			title: [
				...feed.reasons,
				`events arriving now: ${formatLag(feed.lag_p50_s)} old (median, last 15 min)`,
				`last hour: ${feed.received_1h} received, ${feed.repeated_1h} repeats`
			].join("\n")
		})
	}
	if (status.agents) {
		list.push({
			key: "computers",
			label: "Computers reporting",
			icon: "carbon:laptop",
			value: `${status.agents.reporting}/${status.agents.total - status.agents.retired}`,
			tone: status.agents.not_reporting ? "warning" : "neutral",
			title: agentsSummaryTitle(status.agents)
		})
	}
	return list
})

function toneText(tone: Tone) {
	return tone === "error" ? "text-error" : tone === "warning" ? "text-warning" : undefined
}
</script>

<style scoped>
@container (min-width: 48rem) {
	.status-strip {
		grid-template-columns: repeat(var(--cells), minmax(0, 1fr));
	}
}

.cell.is-warn {
	background-color: color-mix(in srgb, var(--warning-color) 7%, transparent);
}

.cell.is-bad {
	background-color: color-mix(in srgb, var(--error-color) 7%, transparent);
}
</style>
