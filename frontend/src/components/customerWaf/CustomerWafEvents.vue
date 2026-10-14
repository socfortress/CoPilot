<template>
	<div class="flex flex-col gap-3">
		<!-- Filters in one row above the results. -->
		<div class="flex flex-wrap items-center gap-2">
			<n-radio-group v-model:value="action" size="small" @update:value="reload()">
				<n-radio-button v-for="o of actionOptions" :key="o.label" :value="o.value">
					{{ o.label }}
				</n-radio-button>
			</n-radio-group>
			<n-input
				v-model:value="clientIp"
				size="small"
				clearable
				placeholder="Client IP"
				class="w-48!"
				@keyup.enter="reload()"
				@clear="clearIp()"
			>
				<template #prefix><Icon :name="SearchIcon" :size="14" /></template>
			</n-input>
			<n-button size="small" secondary :loading @click="reload()">Apply</n-button>
		</div>

		<CustomerWafError v-if="error" :error />

		<section
			v-else
			class="border-default bg-default overflow-hidden rounded-lg border"
			:aria-busy="loading"
			data-testid="waf-events"
		>
			<!-- Column heads: the rows below share this exact grid, so every value lines up. -->
			<div
				class="bg-secondary border-default text-tertiary hidden items-center gap-4 border-b px-4 py-2 md:grid"
				:class="COLUMNS"
			>
				<span :class="HEAD">Time</span>
				<span :class="HEAD">Action</span>
				<span :class="HEAD">Request</span>
				<span :class="HEAD">Client</span>
				<span :class="HEAD" class="text-right">Score</span>
				<span />
			</div>

			<div v-if="loading && !events.length" class="flex flex-col gap-2 p-3">
				<n-skeleton v-for="n of 8" :key="n" :height="44" :sharp="false" class="rounded-md" />
			</div>
			<n-empty
				v-else-if="!events.length"
				description="No events match these filters"
				class="min-h-52 justify-center"
			/>
			<div v-else class="divide-border flex flex-col divide-y transition-opacity" :class="{ 'opacity-50': loading }">
				<!-- An open event closes on its own border and leaves a gap before the next one. -->
				<div
					v-for="e of events"
					:key="e.id"
					:class="{ 'pb-5': expanded.has(e.id) }"
					data-testid="waf-event-row"
				>
					<button
						type="button"
						class="group hover:bg-secondary/50 grid w-full cursor-pointer items-center gap-x-4 gap-y-1.5 border-l-2 px-4 py-2.5 text-left transition-colors md:gap-y-0"
						:class="[COLUMNS_ROW, accent(e.action), { 'bg-secondary/50': expanded.has(e.id) }]"
						:aria-expanded="expanded.has(e.id)"
						@click="toggle(e.id)"
					>
						<n-tooltip>
							<template #trigger>
								<span class="flex flex-col font-mono leading-tight tabular-nums">
									<span class="text-default text-xs">{{ clock(e.timestamp) }}</span>
									<span class="text-tertiary text-2xs">{{ day(e.timestamp) }}</span>
								</span>
							</template>
							{{ formatDate(e.timestamp, dFormats.datetimesec) }} · {{ relative(e.timestamp) }}
						</n-tooltip>

						<span><WafActionPill :action="e.action" /></span>

						<span class="col-span-2 flex min-w-0 flex-col gap-0.5 md:col-span-1">
							<span class="flex min-w-0 items-center gap-2 text-sm">
								<span
									class="border-default text-secondary text-2xs shrink-0 rounded border px-1.5 py-px font-mono tracking-wide"
								>
									{{ e.method }}
								</span>
								<span class="min-w-0 truncate">
									<span class="text-secondary">{{ e.host }}</span>
									<span class="text-default font-mono text-xs">{{ e.uri }}</span>
								</span>
							</span>
							<span v-if="e.matched_rules[0]?.msg" class="text-tertiary flex min-w-0 items-center gap-1.5 text-xs">
								<span v-if="e.matched_rules[0].id" class="font-mono">{{ e.matched_rules[0].id }}</span>
								<span class="truncate">{{ e.matched_rules[0].msg }}</span>
								<span v-if="e.matched_rules.length > 1" class="shrink-0 font-mono">
									+{{ e.matched_rules.length - 1 }}
								</span>
							</span>
						</span>

						<span class="flex min-w-0 flex-col leading-tight">
							<span class="text-default truncate font-mono text-xs">{{ e.client_ip }}</span>
							<span v-if="e.geoip_country_code" class="text-tertiary text-2xs truncate">
								{{ flag(e.geoip_country_code) }} {{ e.geoip_country_name ?? e.geoip_country_code }}
							</span>
						</span>

						<span class="text-right font-mono text-sm tabular-nums" :class="scoreClass(e.anomaly_score)">
							{{ e.anomaly_score ?? "—" }}
						</span>

						<Icon
							:name="ExpandIcon"
							:size="14"
							class="text-tertiary group-hover:text-default justify-self-end transition-transform duration-200"
							:class="{ 'rotate-180': expanded.has(e.id) }"
						/>
					</button>

					<!-- Detail: every fact as label over value, then the rules that matched. -->
					<div
						v-if="expanded.has(e.id)"
						class="bg-secondary/30 border-default flex flex-col gap-4 border-y border-l-2 px-4 pt-4 pb-5"
						:class="accent(e.action)"
						data-testid="waf-event-detail"
					>
						<dl class="grid grid-cols-2 gap-x-6 gap-y-3 md:grid-cols-4">
							<div v-for="fact of details(e)" :key="fact.label" class="flex min-w-0 flex-col gap-0.5">
								<dt :class="HEAD" class="text-tertiary">{{ fact.label }}</dt>
								<dd class="text-default truncate text-xs" :class="{ 'font-mono': fact.mono }">
									{{ fact.value }}
								</dd>
							</div>
						</dl>
						<div v-if="e.matched_rules.length" class="flex flex-col gap-1.5">
							<span :class="HEAD" class="text-tertiary">Matched rules · {{ e.matched_rules.length }}</span>
							<div class="border-default divide-border bg-default divide-y overflow-hidden rounded-md border">
								<div
									v-for="m of e.matched_rules"
									:key="`${m.id}-${m.msg}`"
									class="grid grid-cols-[6rem_minmax(0,1fr)] items-baseline gap-3 px-3 py-1.5 text-xs"
								>
									<span class="text-secondary font-mono">{{ m.id ?? "—" }}</span>
									<span class="text-default">{{ m.msg ?? "" }}</span>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- The WAF returns no total: the page count grows by one while there is a next page. -->
			<footer
				class="bg-secondary border-default flex flex-wrap items-center justify-between gap-3 border-t px-4 py-2"
			>
				<span class="text-tertiary font-mono text-xs tabular-nums" data-testid="waf-events-range">
					{{ rangeLabel }} · newest first
				</span>
				<n-pagination
					v-model:page="page"
					v-model:page-size="pageSize"
					:page-count
					:page-sizes="PAGE_SIZES"
					:page-slot="7"
					:disabled="loading"
					show-size-picker
					size="small"
					data-testid="waf-events-pagination"
				/>
			</footer>
		</section>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CustomerWafAction, CustomerWafEvent, CustomerWafInstance } from "@/types/customer-waf"
import axios from "axios"
import { NButton, NEmpty, NInput, NPagination, NRadioButton, NRadioGroup, NSkeleton, NTooltip } from "naive-ui"
import { computed, onBeforeMount, onBeforeUnmount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils/format"
import CustomerWafError from "./CustomerWafError.vue"
import { flag } from "./utils"
import WafActionPill from "./WafActionPill.vue"

const { customerCode, instance, initialClientIp } = defineProps<{
	customerCode: string
	instance: CustomerWafInstance
	/** Pre-filter, e.g. from "Events from this IP" on the Overview. */
	initialClientIp?: string | null
}>()

const SearchIcon = "carbon:search"
const ExpandIcon = "carbon:chevron-down"
const PAGE_SIZES = [25, 50, 100, 200]
// One grid for the column heads and every row. Narrow screens fold it to two columns.
const COLUMNS = "grid-cols-[6.5rem_7rem_minmax(0,1fr)_11rem_3.5rem_1rem]"
const COLUMNS_ROW = "grid-cols-[auto_1fr] md:grid-cols-[6.5rem_7rem_minmax(0,1fr)_11rem_3.5rem_1rem]"
const HEAD = "text-2xs font-medium tracking-[0.12em] uppercase"
const dFormats = useSettingsStore().dateFormat

// "all" rather than null: radio buttons need a real value.
const actionOptions: { label: string; value: CustomerWafAction | "all" }[] = [
	{ label: "All", value: "all" },
	{ label: "Blocked", value: "blocked" },
	{ label: "Detected", value: "detected" },
	{ label: "Passed", value: "passed" }
]

const loading = ref(false)
const error = ref<ApiError | null>(null)
const events = ref<CustomerWafEvent[]>([])
const page = ref(1)
const pageSize = ref(50)
const hasMore = ref(false)
// The furthest page known to exist, so stepping back does not shrink the page count.
const lastKnownPage = ref(1)
const action = ref<CustomerWafAction | "all">("all")
const clientIp = ref<string | null>(initialClientIp ?? null)
const expanded = ref(new Set<string>())
let controller: AbortController | null = null

const pageCount = computed(() => Math.max(lastKnownPage.value, page.value + (hasMore.value ? 1 : 0)))
const rangeLabel = computed(() => {
	if (!events.value.length) return "0 events"
	const first = (page.value - 1) * pageSize.value + 1
	return `${first.toLocaleString()}–${(first + events.value.length - 1).toLocaleString()}`
})

const relative = (ts: string) => dayjs(ts).fromNow()
const clock = (ts: string) => dayjs(ts).format("HH:mm:ss")
const day = (ts: string) => dayjs(ts).format("D MMM YYYY")

/** A 2px rail on the row's left edge: status at a glance, the pill still says it in words. */
function accent(eventAction: string) {
	if (eventAction === "blocked") return "border-l-error"
	if (eventAction === "detected") return "border-l-warning"
	return "border-l-transparent"
}

function scoreClass(score: number | null) {
	if (score == null || score === 0) return "text-tertiary"
	return score >= 5 ? "text-default font-semibold" : "text-secondary"
}

function details(e: CustomerWafEvent) {
	return [
		{ label: "Timestamp", value: formatDate(e.timestamp, dFormats.datetimesec), mono: true },
		{ label: "Transaction", value: e.transaction_id, mono: true },
		{ label: "Rule", value: e.rule_id ?? "—", mono: true },
		{ label: "Severity", value: e.severity ?? "—", mono: false },
		{ label: "Client IP", value: e.client_ip, mono: true },
		{ label: "Location", value: [e.geoip_city, e.geoip_country_name].filter(Boolean).join(", ") || "—", mono: false },
		{ label: "Anomaly score", value: e.anomaly_score ?? "—", mono: true },
		{ label: "Host", value: e.host || "—", mono: true }
	]
}

function toggle(id: string) {
	const next = new Set(expanded.value)
	if (next.has(id)) next.delete(id)
	else next.add(id)
	expanded.value = next
}

async function load() {
	controller?.abort()
	controller = new AbortController()
	const { signal } = controller
	loading.value = true
	error.value = null
	try {
		// One more than a page: the extra row only says whether a next page exists.
		const res = await Api.customerWaf.getEvents(
			customerCode,
			instance.id,
			{
				action: action.value === "all" ? null : action.value,
				client_ip: clientIp.value?.trim() || null,
				limit: pageSize.value + 1,
				offset: (page.value - 1) * pageSize.value
			},
			signal
		)
		hasMore.value = res.data.events.length > pageSize.value
		events.value = res.data.events.slice(0, pageSize.value)
		lastKnownPage.value = Math.max(lastKnownPage.value, page.value + (hasMore.value ? 1 : 0))
		expanded.value = new Set()
		loading.value = false
	} catch (err) {
		if (axios.isCancel(err)) return
		error.value = err as ApiError
		loading.value = false
	}
}

/** A filter changed: back to the first page, and forget how far the old results went. */
function reload() {
	lastKnownPage.value = 1
	if (page.value !== 1) page.value = 1
	else load()
}

function clearIp() {
	clientIp.value = null
	reload()
}

watch(page, load)
watch(pageSize, reload)

onBeforeMount(load)
onBeforeUnmount(() => controller?.abort())
</script>
