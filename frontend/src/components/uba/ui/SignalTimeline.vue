<template>
	<ol class="signal-timeline relative m-0 flex list-none flex-col gap-2.5 p-0" data-testid="signal-timeline">
		<li
			v-for="item of items"
			:key="item.key"
			class="relative pl-5"
			:class="{ 'is-muted': item.muted }"
			data-testid="signal-item"
		>
			<!-- The rail and this finding's node on it, coloured by how much risk it added. -->
			<span
				class="node absolute top-3.5 left-0 size-2.25 rounded-full"
				:class="RISK_BG_CLASS[pointsTone(item.points)]"
			/>
			<article class="card border-default flex flex-col gap-1.5 rounded-lg border px-3 py-2.5">
				<div class="flex flex-wrap items-center gap-x-2 gap-y-1">
					<time class="text-secondary font-mono text-[11px] tabular-nums">
						{{ formatDate(item.time, dFormats.datetime) }}
					</time>
					<span v-if="item.ruleId" class="rule-chip font-mono text-[11px]">{{ item.ruleId }}</span>
					<n-tag v-if="item.native" size="tiny" :bordered="false">native</n-tag>
					<n-tag v-if="item.suppressed" size="tiny" type="success" :bordered="false">suppressed</n-tag>
					<span
						v-if="item.points != null"
						class="ml-auto font-mono text-xs font-semibold tabular-nums"
						:class="RISK_TEXT_CLASS[pointsTone(item.points)]"
						data-testid="signal-points"
					>
						+{{ riskLabel(item.points) }}
					</span>
				</div>
				<p class="text-default m-0 text-sm leading-snug whitespace-pre-line">{{ item.explanation }}</p>
				<UbaEvidence
					v-if="item.signalId"
					:customer-code
					:signal-id="item.signalId"
					:count="item.evidenceCount ?? 0"
				/>
			</article>
		</li>
	</ol>
</template>

<script setup lang="ts">
// UBA findings in time order on a rail: one card per finding (when, which rule, what it added, the
// sentence UBA wrote) with its source events on demand. Used by the entity and alert drawers so a
// finding reads the same wherever it shows up.
import { NTag } from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import UbaEvidence from "../UbaEvidence.vue"
import { RISK_BG_CLASS, RISK_TEXT_CLASS, riskLabel, riskTone } from "../utils"

export interface SignalTimelineItem {
	key: string
	time: string
	ruleId?: string | null
	explanation: string
	/** Risk the finding added now (decayed); left out for alert updates, which carry none. */
	points?: number | null
	native?: boolean
	suppressed?: boolean
	/** Dimmed: suppressed, or decayed to nothing. */
	muted?: boolean
	signalId?: string
	evidenceCount?: number
}

const { items, customerCode } = defineProps<{ items: SignalTimelineItem[]; customerCode: string }>()

const dFormats = useSettingsStore().dateFormat

/** A single finding is scored against the single-finding scale: 50 is a strong one. */
function pointsTone(points: number | null | undefined) {
	return points == null ? "neutral" : riskTone(points, 33)
}
</script>

<style scoped>
.signal-timeline::before {
	content: "";
	position: absolute;
	top: 0.5rem;
	bottom: 0.5rem;
	left: 4px;
	width: 1px;
	background-color: var(--border-color);
}

.node {
	box-shadow: 0 0 0 3px var(--bg-default-color);
}

.card {
	background-color: var(--bg-default-color);
}

.rule-chip {
	padding: 1px 6px;
	border-radius: 4px;
	background-color: var(--hover-color);
	color: var(--fg-default-color);
}

.is-muted .card {
	opacity: 0.55;
}
</style>
