<template>
	<ul class="activity-list m-0 list-none p-0">
		<li v-for="item of items" :key="item.id" class="row">
			<span class="marker" :style="{ backgroundColor: colorVar(item.status.color) }" />

			<div class="content flex min-w-0 flex-col gap-1">
				<p class="title truncate text-sm font-medium">{{ item.title }}</p>
				<p
					v-if="item.detail"
					class="detail text-secondary text-xs"
					:class="item.detailLines === 2 ? 'line-clamp-2' : 'line-clamp-1'"
				>
					{{ item.detail }}
				</p>
				<p class="meta flex min-w-0 items-center gap-2 font-mono text-xs">
					<span class="status shrink-0" :style="{ color: colorVar(item.status.color) }">
						{{ item.status.label }}
					</span>
					<span v-if="item.meta.length" class="text-tertiary truncate">{{ item.meta.join(" · ") }}</span>
				</p>
			</div>

			<div class="aside flex flex-col items-end justify-between gap-2">
				<time
					class="text-tertiary font-mono text-xs whitespace-nowrap tabular-nums"
					:datetime="toIso(item.time)"
					:title="String(formatDate(item.time, dFormats.datetime))"
				>
					{{ formatTimeAgo(item.time, dFormats.datetime) }}
				</time>
				<div v-if="$slots.action" class="actions">
					<slot name="action" :item />
				</div>
			</div>
		</li>
	</ul>
</template>

<script setup lang="ts">
import type { StatusColor } from "./status"
import { useSettingsStore } from "@/stores/settings"
import { formatDate, formatTimeAgo } from "@/utils/format"
import { colorVar } from "./status"

export interface ActivityItem {
	id: number
	title: string
	/** Shown under the title only when it adds something (alerts often repeat their name here). */
	detail?: string
	detailLines?: 1 | 2
	/** Workflow status or severity: drives the marker and the leading label of the meta line. */
	status: { label: string; color: StatusColor }
	time: string | Date
	meta: string[]
}

defineProps<{
	items: ActivityItem[]
}>()

const dFormats = useSettingsStore().dateFormat

function toIso(time: string | Date) {
	const date = new Date(time)
	return Number.isNaN(date.getTime()) ? undefined : date.toISOString()
}
</script>

<style lang="scss" scoped>
.activity-list {
	container-type: inline-size;

	.row {
		display: grid;
		grid-template-columns: 3px minmax(0, 1fr) auto;
		column-gap: 14px;
		padding: 12px 20px 12px 17px;
		transition: background-color 0.2s ease;

		& + .row {
			border-top: 1px solid var(--border-color);
		}

		// A thin status rail on the leading edge: the colour reads at a glance without
		// a chip competing with the title.
		.marker {
			width: 3px;
			border-radius: 3px;
			align-self: stretch;
			opacity: 0.85;
		}

		.title {
			line-height: 1.35;
		}

		.detail {
			line-height: 1.5;
		}

		.status {
			letter-spacing: 0.02em;
		}

		// Transparent so the button sits on the row surface instead of on a filled
		// box; text keeps the default button colour.
		.actions :deep(.n-button) {
			--n-color: transparent !important;
		}

		&:hover,
		&:focus-within {
			background-color: var(--hover-color);
		}
	}

	// Narrow panels: time and actions drop under the text instead of squeezing it.
	@container (max-width: 440px) {
		.row {
			grid-template-columns: 3px minmax(0, 1fr);
			row-gap: 10px;

			.marker {
				grid-row: span 2;
			}

			.aside {
				grid-column: 2;
				flex-direction: row;
				align-items: center;
			}
		}
	}
}

@media (prefers-reduced-motion: reduce) {
	.activity-list .row {
		transition: none;
	}
}
</style>
