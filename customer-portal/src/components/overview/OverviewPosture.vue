<template>
	<section
		class="posture bg-default border-default grid overflow-hidden rounded-lg border"
		aria-label="Security posture"
	>
		<RouterLink
			v-for="cell of cells"
			:key="cell.key"
			:to="{ name: cell.route }"
			class="cell group flex min-w-0 flex-col gap-4 p-5"
		>
			<div class="flex items-center justify-between gap-2">
				<div class="text-secondary flex items-center gap-2 text-sm font-medium">
					<Icon :name="cell.icon" :size="16" />
					{{ cell.title }}
				</div>
				<Icon
					name="carbon:arrow-up-right"
					:size="14"
					class="text-tertiary opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100"
				/>
			</div>

			<p v-if="cell.error" class="text-error text-sm">{{ cell.error }}</p>

			<template v-else-if="!loaded && cell.loading">
				<!-- Same heights as the loaded cell (34 / 6 / 16), so data arriving causes no layout shift. -->
				<n-skeleton :height="34" :width="96" :sharp="false" />
				<n-skeleton :height="6" :sharp="false" />
				<n-skeleton :height="16" :width="220" :sharp="false" />
			</template>

			<template v-else>
				<div class="flex items-baseline gap-2">
					<span class="headline font-mono tabular-nums">{{ cell.headline }}</span>
					<span class="text-secondary text-sm">{{ cell.headlineCaption }}</span>
				</div>

				<StatusBar :segments="cell.segments" />

				<div class="flex flex-wrap items-center justify-between gap-x-4 gap-y-1.5">
					<ul class="m-0 flex list-none flex-wrap items-center gap-x-3 gap-y-1 p-0">
						<li
							v-for="segment of cell.segments"
							:key="segment.key"
							class="text-secondary flex items-center gap-1.5 text-xs"
						>
							<span class="dot" :style="{ backgroundColor: colorVar(segment.color) }" />
							<span class="text-default font-mono tabular-nums">{{ segment.value }}</span>
							{{ segment.label }}
						</li>
					</ul>
					<span class="text-tertiary font-mono text-xs tabular-nums">{{ cell.footnote }}</span>
				</div>
			</template>
		</RouterLink>
	</section>
</template>

<script setup lang="ts">
import type { StatusSegment } from "./status"
import type { AgentCounts, StatusCounts } from "@/composables/overview/useOverviewData"
import { NSkeleton } from "naive-ui"
import { computed } from "vue"
import { RouterLink } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import { ICONS } from "@/const"
import { colorVar } from "./status"
import StatusBar from "./StatusBar.vue"

interface PostureCell {
	key: string
	title: string
	icon: string
	route: string
	/** The number that needs attention, not the grand total. */
	headline: string
	headlineCaption: string
	segments: StatusSegment[]
	footnote: string
	loading: boolean
	error: string | null
}

const { alertCounts, caseCounts, agentCounts, loading, errors, loaded } = defineProps<{
	alertCounts: StatusCounts
	caseCounts: StatusCounts
	agentCounts: AgentCounts
	loading: { alerts: boolean; cases: boolean; agents: boolean }
	errors: { alerts: string | null; cases: string | null; agents: string | null }
	loaded: boolean
}>()

// Same status colours as the alert and case lists (getStatusColor), so a colour
// means the same thing on every page.
function statusSegments(counts: StatusCounts): StatusSegment[] {
	return [
		{ key: "open", label: "open", value: counts.open, color: "info" },
		{ key: "in_progress", label: "in progress", value: counts.in_progress, color: "warning" },
		{ key: "closed", label: "closed", value: counts.closed, color: "success" }
	]
}

const cells = computed<PostureCell[]>(() => [
	{
		key: "alerts",
		title: "Alerts",
		icon: ICONS.alerts,
		route: "AlertsList",
		headline: String(alertCounts.open),
		headlineCaption: alertCounts.open === 1 ? "open alert" : "open alerts",
		segments: statusSegments(alertCounts),
		footnote: `${alertCounts.total} total`,
		loading: loading.alerts,
		error: errors.alerts
	},
	{
		key: "cases",
		title: "Cases",
		icon: ICONS.cases,
		route: "CasesList",
		headline: String(caseCounts.open),
		headlineCaption: caseCounts.open === 1 ? "open case" : "open cases",
		segments: statusSegments(caseCounts),
		footnote: `${caseCounts.total} total`,
		loading: loading.cases,
		error: errors.cases
	},
	{
		key: "agents",
		title: "Agents",
		icon: ICONS.agents,
		route: "AgentsList",
		headline: `${agentCounts.online}/${agentCounts.total}`,
		headlineCaption: "online",
		segments: [
			{ key: "online", label: "online", value: agentCounts.online, color: "success" },
			{ key: "offline", label: "offline", value: agentCounts.offline, color: "error" }
		],
		footnote: `${agentCounts.critical} critical`,
		loading: loading.agents,
		error: errors.agents
	}
])
</script>

<style lang="scss" scoped>
.posture {
	grid-template-columns: 1fr;

	@media (min-width: 900px) {
		grid-template-columns: repeat(3, minmax(0, 1fr));
	}

	.cell {
		color: inherit;
		text-decoration: none;
		transition: background-color 0.2s ease;

		& + .cell {
			border-top: 1px solid var(--border-color);

			@media (min-width: 900px) {
				border-top: none;
				border-left: 1px solid var(--border-color);
			}
		}

		&:hover {
			background-color: var(--hover-color);
		}

		&:focus-visible {
			outline: 2px solid var(--primary-color);
			outline-offset: -2px;
		}
	}

	.headline {
		font-size: 2.125rem;
		font-weight: 600;
		line-height: 1;
		letter-spacing: -0.03em;
	}

	.dot {
		width: 6px;
		height: 6px;
		border-radius: 2px;
		flex-shrink: 0;
	}
}
</style>
