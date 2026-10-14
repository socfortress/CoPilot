<template>
	<div class="flex flex-col gap-3">
		<div class="flex flex-wrap items-center gap-2">
			<n-input v-model:value="query" size="small" clearable placeholder="Filter by IP or country" class="w-60!">
				<template #prefix><Icon :name="SearchIcon" :size="14" /></template>
			</n-input>
			<n-checkbox v-model:checked="hideBlocked" size="small">Hide already blocked</n-checkbox>
			<div v-if="summary" class="ml-auto flex flex-wrap items-center gap-2">
				<Badge type="splitted" size="small">
					<template #label>scored</template>
					<template #value>
						<span class="font-mono tabular-nums">{{ summary.total_ips.toLocaleString() }} IPs</span>
					</template>
				</Badge>
				<Badge v-if="summary.window_days" type="splitted" size="small">
					<template #label>window</template>
					<template #value>{{ summary.window_days }}d</template>
				</Badge>
				<Badge v-if="summary.last_run_at" type="splitted" size="small">
					<template #label>updated</template>
					<template #value>{{ relative(summary.last_run_at) }}</template>
				</Badge>
			</div>
		</div>

		<CustomerWafError v-if="error" :error />

		<section
			v-else
			class="border-default bg-default @container overflow-hidden rounded-lg border"
			:aria-busy="loading"
			data-testid="waf-threat-intel"
		>
			<!-- Column heads share the rows' grid, so every value lines up under its head. -->
			<div
				class="bg-secondary border-default text-tertiary hidden items-center gap-4 border-b px-4 py-2 @4xl:grid"
				:class="COLUMNS"
			>
				<span :class="HEAD">#</span>
				<span :class="HEAD">Source</span>
				<span :class="HEAD">Threat score</span>
				<span :class="HEAD">Activity</span>
				<span :class="HEAD">Last seen</span>
				<span :class="HEAD" class="text-right">Status</span>
			</div>

			<div v-if="loading" class="flex flex-col gap-2 p-3">
				<n-skeleton v-for="n of 8" :key="n" :height="44" :sharp="false" class="rounded-md" />
			</div>
			<n-empty
				v-else-if="!visible.length"
				:description="entries.length ? 'No offender matches' : 'No offenders'"
				class="min-h-52 justify-center"
			/>
			<div v-else class="divide-border flex flex-col divide-y">
				<div
					v-for="(e, index) of pageRows"
					:key="e.ip_address"
					class="hover:bg-secondary/50 grid items-center gap-x-3 gap-y-2 px-4 py-2.5 transition-colors @4xl:gap-x-4"
					:class="COLUMNS_ROW"
					data-testid="waf-offender-row"
				>
					<span class="text-tertiary font-mono text-xs tabular-nums [grid-area:rank]">
						{{ String(rankOffset + index + 1).padStart(2, "0") }}
					</span>

					<!-- Narrow: address and country on one line; wide: stacked in their column. -->
					<span
						class="flex min-w-0 items-baseline gap-2 leading-tight [grid-area:source] @4xl:flex-col @4xl:items-start @4xl:gap-0"
					>
						<span class="text-default shrink-0 font-mono text-sm @4xl:shrink @4xl:truncate">
							{{ e.ip_address }}
						</span>
						<span class="text-tertiary text-2xs truncate">
							{{ flag(e.country_code) }} {{ e.country_name ?? e.country_code ?? "Unknown" }}
						</span>
					</span>

					<span class="flex min-w-0 items-center gap-3 [grid-area:score]">
						<span
							class="text-default shrink-0 font-mono text-sm font-semibold tabular-nums @4xl:w-9 @4xl:text-right"
						>
							{{ e.threat_score }}
						</span>
						<span class="h-1 min-w-0 grow overflow-hidden rounded-full" :style="{ background: trackColor }">
							<span
								class="block h-full rounded-full"
								:style="{
									width: `${Math.max(2, (e.threat_score / maxScore) * 100)}%`,
									background: markColor
								}"
							/>
						</span>
					</span>

					<span class="flex min-w-0 flex-col gap-0.5 leading-tight [grid-area:activity]">
						<span class="flex items-baseline gap-1.5 font-mono text-xs tabular-nums">
							<span :class="e.block_count ? 'text-error' : 'text-secondary'">
								{{ e.block_count.toLocaleString() }}
							</span>
							<span class="text-secondary">blocked /</span>
							<span class="text-default">{{ e.total_events.toLocaleString() }}</span>
							<span class="text-secondary">events</span>
						</span>
						<span
							v-if="e.top_rules.length"
							class="text-tertiary text-2xs flex min-w-0 gap-2 truncate font-mono"
						>
							<span v-for="r of e.top_rules.slice(0, 2)" :key="r.rule_id ?? 'none'">
								{{ r.rule_id ?? "—" }}×{{ r.count }}
							</span>
							<span v-if="e.top_rules.length > 2">+{{ e.top_rules.length - 2 }}</span>
						</span>
					</span>

					<n-tooltip>
						<template #trigger>
							<span
								class="text-secondary justify-self-end text-xs whitespace-nowrap [grid-area:seen] @4xl:justify-self-start"
							>
								{{ relative(e.last_seen_at) }}
							</span>
						</template>
						first seen {{ formatDate(e.first_seen_at, dFormats.datetime) }} · last seen
						{{ formatDate(e.last_seen_at, dFormats.datetime) }}
					</n-tooltip>

					<span class="flex justify-end [grid-area:status]">
						<span
							v-if="e.is_blocked"
							class="border-default text-secondary text-2xs inline-flex items-center gap-1 rounded border px-2 py-0.5 tracking-wide uppercase"
						>
							<Icon :name="BlockIcon" :size="11" />
							blocked
						</span>
						<n-button
							v-else-if="canBlock"
							size="tiny"
							type="error"
							secondary
							@click="openBlock(e.ip_address)"
						>
							<template #icon><Icon :name="BlockIcon" :size="12" /></template>
							Block
						</n-button>
					</span>
				</div>
			</div>

			<footer
				v-if="visible.length"
				class="bg-secondary border-default flex flex-wrap items-center justify-between gap-3 border-t px-4 py-2"
			>
				<span class="text-tertiary font-mono text-xs tabular-nums" data-testid="waf-offenders-range">
					{{ rangeLabel }} · by threat score
				</span>
				<n-pagination
					v-model:page="page"
					v-model:page-size="pageSize"
					:item-count="visible.length"
					:page-sizes="PAGE_SIZES"
					:page-slot="7"
					show-size-picker
					size="small"
					data-testid="waf-offenders-pagination"
				/>
			</footer>
		</section>

		<CustomerWafBlockDialog
			v-model:show="showBlock"
			:customer-code
			:instances="[instance]"
			:initial-target="blockTarget"
			@blocked="emit('blocked')"
		/>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type {
	CustomerWafInstance,
	CustomerWafThreatIntelEntry,
	CustomerWafThreatIntelSummary
} from "@/types/customer-waf"
import { NButton, NCheckbox, NEmpty, NInput, NPagination, NSkeleton, NTooltip } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils/format"
import { useWafChartColors } from "./chart-colors"
import CustomerWafBlockDialog from "./CustomerWafBlockDialog.vue"
import CustomerWafError from "./CustomerWafError.vue"
import { capabilitiesFromRoles, flag } from "./utils"

const { customerCode, instance } = defineProps<{ customerCode: string; instance: CustomerWafInstance }>()
const emit = defineEmits<{ (e: "blocked"): void }>()

const SearchIcon = "carbon:search"
const BlockIcon = "carbon:locked"
const PAGE_SIZES = [25, 50, 100]
// One grid for the column heads and every row. Narrow screens fold it to two columns.
const COLUMNS = "grid-cols-[2rem_minmax(0,1.1fr)_minmax(0,1.3fr)_minmax(0,1.2fr)_6.5rem_6rem]"
// Rows place every cell by area (by the list's own width, not the window's: the sidebar
// takes a variable share of it): narrow, a small card (rank, address and status on top, the
// score's meter across, then activity and last seen); wide, one line under the column heads.
const COLUMNS_ROW = [
	"grid-cols-[auto_minmax(0,1fr)_auto]",
	"[grid-template-areas:'rank_source_status'_'score_score_score'_'activity_activity_seen']",
	"@4xl:grid-cols-[2rem_minmax(0,1.1fr)_minmax(0,1.3fr)_minmax(0,1.2fr)_6.5rem_6rem]",
	"@4xl:[grid-template-areas:'rank_source_score_activity_seen_status']"
].join(" ")
const HEAD = "text-2xs font-medium tracking-[0.12em] uppercase"
const dFormats = useSettingsStore().dateFormat
const { markColor, trackColor } = useWafChartColors()

const loading = ref(false)
const error = ref<ApiError | null>(null)
const summary = ref<CustomerWafThreatIntelSummary | null>(null)
const entries = ref<CustomerWafThreatIntelEntry[]>([])
const query = ref("")
const hideBlocked = ref(false)
const showBlock = ref(false)
const blockTarget = ref("")
const page = ref(1)
const pageSize = ref(25)

const canBlock = computed(() => capabilitiesFromRoles(instance.last_verified_role).can_block)
const maxScore = computed(() => Math.max(1, ...entries.value.map(e => e.threat_score)))
// Highest threat first, whatever order the WAF sent: the rank column reads it.
const visible = computed(() => {
	const q = query.value.trim().toLowerCase()
	return entries.value
		.filter(
			e =>
				(!hideBlocked.value || !e.is_blocked) &&
				(!q ||
					e.ip_address.includes(q) ||
					(e.country_name ?? "").toLowerCase().includes(q) ||
					(e.country_code ?? "").toLowerCase() === q)
		)
		.sort((a, b) => b.threat_score - a.threat_score)
})
const rankOffset = computed(() => (page.value - 1) * pageSize.value)
const pageRows = computed(() => visible.value.slice(rankOffset.value, rankOffset.value + pageSize.value))
const rangeLabel = computed(() => {
	const last = Math.min(rankOffset.value + pageSize.value, visible.value.length)
	return `${(rankOffset.value + 1).toLocaleString()}–${last.toLocaleString()} of ${visible.value.length.toLocaleString()}`
})

const relative = (ts: string) => dayjs(ts).fromNow()

// A narrower filter starts again from the top.
watch([query, hideBlocked, pageSize], () => {
	page.value = 1
})

function openBlock(ip: string) {
	blockTarget.value = ip
	showBlock.value = true
}

onBeforeMount(async () => {
	loading.value = true
	try {
		const res = await Api.customerWaf.getThreatIntel(customerCode, instance.id)
		summary.value = res.data.summary
		entries.value = res.data.entries
	} catch (err) {
		error.value = err as ApiError
	} finally {
		loading.value = false
	}
})
</script>
