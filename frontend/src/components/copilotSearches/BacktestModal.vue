<template>
	<n-modal
		:show
		preset="card"
		segmented
		:mask-closable="!running"
		:style="{ width: 'min(960px, 95vw)', maxHeight: '92vh' }"
		content-class="p-0!"
		@update:show="onShow"
	>
		<template #header>
			<div class="flex items-center gap-2">
				<Icon :name="BacktestIcon" :size="20" />
				<span class="font-semibold">Backtest rule</span>
				<n-tag size="tiny" round :bordered="false" type="info">Graylog-only</n-tag>
			</div>
		</template>

		<div class="flex max-h-[78vh] flex-col">
			<!-- Config bar -->
			<div class="border-default flex flex-wrap items-end gap-3 border-b px-5 py-4">
				<div class="flex min-w-55 grow flex-col gap-1">
					<span class="text-secondary text-xs font-medium">Customer</span>
					<n-select
						v-model:value="customerCode"
						:options="customerOptions"
						:loading="loadingCustomers"
						filterable
						placeholder="Select a customer"
					/>
				</div>
				<div class="flex flex-col gap-1">
					<span class="text-secondary text-xs font-medium">Look-back</span>
					<n-select
						v-model:value="rangeSeconds"
						:options="rangeOptions"
						class="w-30!"
						:consistent-menu-width="false"
					/>
				</div>
				<n-button type="primary" :loading="running" :disabled="!customerCode || running" @click="runBacktest">
					<template #icon><Icon :name="RunIcon" :size="16" /></template>
					Run backtest
				</n-button>
			</div>

			<!-- Body -->
			<n-scrollbar class="grow" style="max-height: calc(78vh - 74px)">
				<div class="px-5 py-4">
					<!-- idle -->
					<n-empty
						v-if="!result && !running && !errorMsg"
						description="Pick a customer and run the backtest to see how this rule would behave against their real Graylog data."
						class="py-20"
					>
						<template #icon><Icon :name="BacktestIcon" :size="42" /></template>
					</n-empty>

					<!-- running -->
					<div v-else-if="running" class="flex flex-col items-center gap-3 py-20">
						<n-spin :size="30" />
						<span class="text-secondary text-sm">Querying Graylog… this can take a few seconds.</span>
					</div>

					<!-- error -->
					<n-alert v-else-if="errorMsg" type="error" :bordered="false" title="Backtest failed">
						{{ errorMsg }}
					</n-alert>

					<!-- results -->
					<div v-else-if="result" class="flex flex-col gap-6">
						<n-alert v-if="result.note" type="warning" :bordered="false" size="small">
							{{ result.note }}
						</n-alert>

						<n-alert
							v-if="result.missing_fields?.length"
							type="warning"
							:bordered="false"
							size="small"
							title="Fields not found in this customer's data"
						>
							<span class="text-sm">
								<code v-for="(f, i) of result.missing_fields" :key="f">
									{{ f }}{{ i < result.missing_fields.length - 1 ? ", " : "" }}
								</code>
								— the rule may never match for this customer. Check for typos or a different field
								naming.
							</span>
						</n-alert>

						<!-- headline stats -->
						<div class="grid grid-cols-2 gap-3 md:grid-cols-4">
							<CardStats v-for="(s, i) of statTiles" :key="i" :title="s.title" :value="s.value">
								<template #icon>
									<CardStatsIcon :icon-name="s.icon" boxed :color="s.color" :box-size="42" />
								</template>
							</CardStats>
						</div>

						<!-- sparkline -->
						<section v-if="result.per_bucket.length" class="flex flex-col gap-2">
							<h4 class="section-title">
								Matches per {{ result.bucket_unit === "1h" ? "hour" : "day" }}
							</h4>
							<div class="border-default bg-secondary/40 rounded-lg border p-2">
								<ChartColumn
									:labels="bucketLabels"
									:data="bucketData"
									height="180px"
									labels-datetime
									monochrome
								/>
							</div>
						</section>

						<!-- aggregation simulation -->
						<section
							v-if="result.mode === 'aggregation' && result.aggregation"
							class="rounded-xl border p-4"
							:style="{ borderColor: `${warningColor}55`, background: `${warningColor}0d` }"
						>
							<div class="mb-3 flex flex-wrap items-center gap-2">
								<Icon :name="AlertIcon" :size="18" :style="{ color: warningColor }" />
								<span class="font-semibold">Threshold simulation</span>
								<n-tag size="small" round :bordered="false">
									{{ result.aggregation.function
									}}{{ result.aggregation.field ? `(${result.aggregation.field})` : "()" }}
									{{ result.aggregation.condition }} {{ result.aggregation.threshold }} per
									{{ result.aggregation.window }}
									<template v-if="result.aggregation.group_by.length">
										by {{ result.aggregation.group_by.join(", ") }}
									</template>
								</n-tag>
							</div>

							<div class="mb-4 flex flex-wrap items-end gap-8">
								<div class="flex flex-col">
									<span class="text-secondary text-xs">Would have fired</span>
									<span class="font-display text-3xl font-bold" :style="{ color: warningColor }">
										≈ {{ fmt(result.aggregation.estimated_alerts) }}
									</span>
									<span class="text-secondary text-xs">
										alert{{ result.aggregation.estimated_alerts === 1 ? "" : "s" }} in
										{{ rangeLabel }}
									</span>
								</div>
								<div class="flex flex-col">
									<span class="text-secondary text-xs">Per day</span>
									<span class="font-display text-3xl font-bold">
										{{ result.aggregation.per_day_alerts }}
									</span>
								</div>
							</div>

							<!-- top offenders -->
							<div v-if="result.aggregation.top_offenders.length" class="mb-4 flex flex-col gap-2">
								<h4 class="section-title">Top offenders</h4>
								<div
									v-for="(o, i) of result.aggregation.top_offenders"
									:key="i"
									class="flex items-center gap-3"
								>
									<code class="w-56 shrink-0 truncate text-xs">{{ o.group }}</code>
									<div class="bg-secondary h-2.5 grow overflow-hidden rounded-full">
										<div
											class="h-full rounded-full"
											:style="{
												width: pct(o.windows_alerting, maxOffenderWindows),
												background: warningColor
											}"
										/>
									</div>
									<span class="text-secondary w-24 shrink-0 text-right text-xs">
										peak
										<b class="text-default">{{ o.peak }}</b>
										· {{ o.windows_alerting }}×
									</span>
								</div>
							</div>

							<!-- threshold sensitivity -->
							<div v-if="result.aggregation.sensitivity.length" class="flex flex-col gap-2">
								<h4 class="section-title">Threshold sensitivity</h4>
								<div class="flex flex-wrap gap-2">
									<div
										v-for="(s, i) of result.aggregation.sensitivity"
										:key="i"
										class="flex min-w-16 flex-col items-center rounded-lg border px-3 py-2"
										:class="
											s.threshold === result.aggregation.threshold
												? 'border-primary'
												: 'border-default'
										"
										:style="
											s.threshold === result.aggregation.threshold
												? { background: `${primaryColor}14` }
												: {}
										"
									>
										<span class="text-secondary text-xs">≥ {{ s.threshold }}</span>
										<span class="font-display text-lg font-bold">{{ fmt(s.alerts) }}</span>
									</div>
								</div>
								<span class="text-secondary text-xs">
									Alerts at each threshold — the outlined one is the rule's current setting.
								</span>
							</div>
						</section>

						<!-- top fields -->
						<section v-if="topFieldEntries.length" class="flex flex-col gap-2">
							<h4 class="section-title">Top values (from sampled events)</h4>
							<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
								<div
									v-for="[field, values] of topFieldEntries"
									:key="field"
									class="border-default rounded-lg border p-3"
								>
									<code class="mb-2 block text-xs font-semibold">{{ field }}</code>
									<div class="flex flex-col gap-2">
										<div v-for="(v, i) of values" :key="i" class="flex items-center gap-2">
											<span class="w-40 shrink-0 truncate text-sm" :title="v.value">
												{{ v.value }}
											</span>
											<div class="bg-secondary h-2 grow overflow-hidden rounded-full">
												<div
													class="h-full rounded-full"
													:style="{
														width: pct(v.count, maxTopCount(values)),
														background: primaryColor
													}"
												/>
											</div>
											<span class="text-secondary w-8 shrink-0 text-right text-xs">
												{{ v.count }}
											</span>
										</div>
									</div>
								</div>
							</div>
						</section>

						<!-- samples -->
						<section v-if="result.samples.length" class="flex flex-col gap-2">
							<div class="flex items-center gap-2">
								<h4 class="section-title">Sample events ({{ result.samples.length }})</h4>
								<span class="text-secondary text-xs">— click a row to inspect the full log</span>
							</div>
							<n-data-table
								:columns="sampleColumns"
								:data="result.samples"
								bordered
								size="small"
								:max-height="280"
								:row-props
								:scroll-x="Math.max(640, sampleColumns.length * 170)"
							/>
						</section>

						<n-empty
							v-else-if="!result.total_hits"
							description="No matching events in this window — the rule would not have fired."
							class="py-10"
						>
							<template #icon><Icon :name="EmptyIcon" :size="36" /></template>
						</n-empty>
					</div>
				</div>
			</n-scrollbar>
		</div>
	</n-modal>

	<!-- Full-event inspector -->
	<n-modal
		:show="!!detailEvent"
		preset="card"
		segmented
		:style="{ width: 'min(780px, 94vw)', maxHeight: '90vh' }"
		content-class="p-0!"
		@update:show="
			(v: boolean) => {
				if (!v) detailEvent = null
			}
		"
	>
		<template #header>
			<div class="flex items-center gap-2">
				<Icon :name="LogIcon" :size="18" />
				<span class="font-semibold">Event details</span>
				<n-tag v-if="detailEvent?.source" size="tiny" round :bordered="false">{{ detailEvent?.source }}</n-tag>
			</div>
		</template>
		<template #header-extra>
			<n-button size="tiny" secondary @click="copyEventJson">
				<template #icon><Icon :name="CopyIcon" :size="14" /></template>
				Copy JSON
			</n-button>
		</template>

		<div class="border-default border-b px-4 pt-3 pb-3">
			<n-input v-model:value="detailFilter" size="small" clearable placeholder="Filter fields…">
				<template #prefix><Icon :name="SearchIcon" :size="14" /></template>
			</n-input>
		</div>
		<n-scrollbar style="max-height: 68vh">
			<div class="flex flex-col gap-4 p-4">
				<div v-if="filteredPrimary.length" class="flex flex-col">
					<div
						v-for="[k, v] of filteredPrimary"
						:key="k"
						class="kv-row"
						title="Click the value to copy"
						@click="copyVal(v)"
					>
						<code class="kv-key">{{ k }}</code>
						<span class="kv-val">{{ v }}</span>
					</div>
				</div>

				<n-empty
					v-if="!filteredPrimary.length && !filteredInternal.length"
					description="No fields match your filter."
					class="py-8"
				/>

				<n-collapse v-if="filteredInternal.length" :default-expanded-names="detailFilter ? ['internal'] : []">
					<n-collapse-item :title="`Graylog internal fields (${filteredInternal.length})`" name="internal">
						<div class="flex flex-col">
							<div
								v-for="[k, v] of filteredInternal"
								:key="k"
								class="kv-row"
								title="Click the value to copy"
								@click="copyVal(v)"
							>
								<code class="kv-key">{{ k }}</code>
								<span class="kv-val">{{ v }}</span>
							</div>
						</div>
					</n-collapse-item>
				</n-collapse>
			</div>
		</n-scrollbar>
	</n-modal>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { BacktestResponse, BacktestTopValue } from "@/types/copilot-searches"
import {
	NAlert,
	NButton,
	NCollapse,
	NCollapseItem,
	NDataTable,
	NEmpty,
	NInput,
	NModal,
	NScrollbar,
	NSelect,
	NSpin,
	NTag,
	useMessage
} from "naive-ui"
import { computed, h, ref, watch } from "vue"
import Api from "@/api"
import CardStats from "@/components/common/cards/CardStats.vue"
import CardStatsIcon from "@/components/common/cards/CardStatsIcon.vue"
import ChartColumn from "@/components/common/charts/ChartColumn.vue"
import Icon from "@/components/common/Icon.vue"
import { useThemeStore } from "@/stores/theme"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	show: boolean
	yaml: string
}>()
const emit = defineEmits<{
	(e: "update:show", value: boolean): void
}>()

const BacktestIcon = "carbon:chart-line"
const RunIcon = "carbon:play-filled-alt"
const AlertIcon = "carbon:warning-alt"
const LogIcon = "carbon:document"
const CopyIcon = "carbon:copy"
const EmptyIcon = "carbon:search"
const SearchIcon = "carbon:search"

const message = useMessage()
const themeStore = useThemeStore()
const primaryColor = computed(() => themeStore.style["primary-color"])
const warningColor = computed(() => themeStore.style["warning-color"])
const successColor = computed(() => themeStore.style["success-color"])
const infoColor = computed(() => themeStore.style["info-color"] || themeStore.style["primary-color"])
const mutedColor = computed(() => themeStore.style["fg-secondary-color"])

// --- state ---
const customerCode = ref<string | null>(null)
const rangeSeconds = ref<number>(604800)
const loadingCustomers = ref(false)
const customerOptions = ref<{ label: string; value: string }[]>([])
const running = ref(false)
const result = ref<BacktestResponse | null>(null)
const errorMsg = ref<string | null>(null)
const detailEvent = ref<Record<string, unknown> | null>(null)
const detailFilter = ref("")

const rangeOptions = [
	{ label: "Last 24 hours", value: 86400 },
	{ label: "Last 3 days", value: 259200 },
	{ label: "Last 7 days", value: 604800 },
	{ label: "Last 14 days", value: 1209600 },
	{ label: "Last 30 days", value: 2592000 }
]

const rangeLabel = computed(() => {
	const s = result.value?.range_seconds ?? rangeSeconds.value
	const d = Math.round(s / 86400)
	return d >= 1 ? `${d}d` : `${Math.round(s / 3600)}h`
})

function fmt(n: number): string {
	return (n ?? 0).toLocaleString()
}
function pct(n: number, max: number): string {
	return `${Math.max(3, Math.round((n / Math.max(1, max)) * 100))}%`
}

// --- headline stat tiles ---
const statTiles = computed(() => {
	const r = result.value
	if (!r) return []
	const tiles = [
		{ title: "Total matches", value: fmt(r.total_hits), icon: "carbon:search", color: primaryColor.value },
		{ title: "Avg / day", value: String(r.per_day_avg), icon: "carbon:calendar", color: successColor.value },
		{ title: "Window", value: rangeLabel.value, icon: "carbon:time", color: mutedColor.value }
	]
	if (r.mode === "aggregation") {
		tiles.push({
			title: "Est. alerts",
			value: fmt(r.aggregation?.estimated_alerts ?? 0),
			icon: "carbon:warning-alt",
			color: warningColor.value
		})
	} else {
		tiles.push({ title: "Analyzed", value: fmt(r.fetched), icon: "carbon:list-checked", color: infoColor.value })
	}
	return tiles
})

// --- sparkline ---
const bucketLabels = computed(() => (result.value?.per_bucket || []).map(b => b.bucket))
const bucketData = computed(() => (result.value?.per_bucket || []).map(b => b.count))

// --- top values / offenders ---
const topFieldEntries = computed<[string, BacktestTopValue[]][]>(() =>
	result.value ? Object.entries(result.value.top_fields || {}) : []
)
function maxTopCount(values: BacktestTopValue[]): number {
	return Math.max(1, ...values.map(v => v.count))
}
const maxOffenderWindows = computed(() =>
	Math.max(1, ...(result.value?.aggregation?.top_offenders || []).map(o => o.windows_alerting))
)

// --- samples table ---
const sampleColumns = computed(() => {
	const fields = (result.value?.sample_fields || []).slice(0, 6)
	const cols: any[] = fields.map(f => ({
		title: f,
		key: f,
		ellipsis: { tooltip: true },
		render: (row: Record<string, unknown>) => {
			const v = row[f]
			return h("span", { class: "text-xs" }, v === null || v === undefined ? "" : String(v))
		}
	}))
	cols.push({
		title: "",
		key: "_chevron",
		width: 36,
		align: "center",
		render: () => h(Icon, { name: "carbon:chevron-right", size: 14, class: "text-secondary" })
	})
	return cols
})

function rowProps(row: Record<string, unknown>) {
	return {
		style: "cursor: pointer",
		onClick: () => {
			detailFilter.value = ""
			detailEvent.value = row
		}
	}
}

// --- event inspector ---
const PRIMARY_ORDER = ["timestamp", "source", "message", "full_message"]
function isInternal(key: string): boolean {
	return key.startsWith("gl2_") || key === "streams"
}
function fmtVal(v: unknown): string {
	if (v === null || v === undefined) return ""
	if (typeof v === "object") return JSON.stringify(v)
	return String(v)
}
const primaryEntries = computed<[string, string][]>(() => {
	const ev = detailEvent.value
	if (!ev) return []
	const out: [string, string][] = []
	for (const k of PRIMARY_ORDER) {
		if (k in ev && fmtVal(ev[k]) !== "") out.push([k, fmtVal(ev[k])])
	}
	for (const k of Object.keys(ev)
		.filter(k => !PRIMARY_ORDER.includes(k) && !isInternal(k))
		.sort()) {
		out.push([k, fmtVal(ev[k])])
	}
	return out
})
const internalEntries = computed<[string, string][]>(() => {
	const ev = detailEvent.value
	if (!ev) return []
	return Object.keys(ev)
		.filter(isInternal)
		.sort()
		.map(k => [k, fmtVal(ev[k])] as [string, string])
})
function matchFilter(entries: [string, string][]): [string, string][] {
	const q = detailFilter.value.trim().toLowerCase()
	if (!q) return entries
	return entries.filter(([k, v]) => k.toLowerCase().includes(q) || v.toLowerCase().includes(q))
}
const filteredPrimary = computed(() => matchFilter(primaryEntries.value))
const filteredInternal = computed(() => matchFilter(internalEntries.value))

async function copyVal(v: string) {
	try {
		await navigator.clipboard.writeText(v)
		message.success("Value copied")
	} catch {
		message.error("Couldn't copy to clipboard")
	}
}
async function copyEventJson() {
	if (!detailEvent.value) return
	try {
		await navigator.clipboard.writeText(JSON.stringify(detailEvent.value, null, 2))
		message.success("Event JSON copied to clipboard")
	} catch {
		message.error("Couldn't copy to clipboard")
	}
}

// --- data ---
async function loadCustomers() {
	loadingCustomers.value = true
	try {
		const res = await Api.customers.getCustomers({})
		const customers = res.data.customers || []
		customerOptions.value = customers.map(c => ({
			label: `${c.customer_name} (${c.customer_code})`,
			value: c.customer_code
		}))
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to load customers")
	} finally {
		loadingCustomers.value = false
	}
}

async function runBacktest() {
	if (!customerCode.value) return
	running.value = true
	errorMsg.value = null
	result.value = null
	detailEvent.value = null
	try {
		const res = await Api.copilotSearches.backtestRule({
			yaml: props.yaml,
			customer_code: customerCode.value,
			range_seconds: rangeSeconds.value
		})
		if (res.data.success) {
			result.value = res.data
		} else {
			errorMsg.value = res.data.error || res.data.message || "Backtest failed."
		}
	} catch (err) {
		errorMsg.value = getApiErrorMessage(err as ApiError) || "Backtest request failed."
	} finally {
		running.value = false
	}
}

function onShow(value: boolean) {
	emit("update:show", value)
}

watch(
	() => props.show,
	shown => {
		if (shown && !customerOptions.value.length) loadCustomers()
	}
)
</script>

<style scoped>
.section-title {
	font-size: 11px;
	font-weight: 600;
	letter-spacing: 0.06em;
	text-transform: uppercase;
	color: var(--n-text-color-3, #888);
}
.kv-row {
	display: grid;
	grid-template-columns: minmax(140px, 240px) minmax(0, 1fr);
	gap: 12px;
	padding: 6px 0;
	border-bottom: 1px solid var(--n-border-color, rgba(128, 128, 128, 0.15));
	align-items: start;
}
.kv-row:last-child {
	border-bottom: 0;
}
.kv-key {
	font-size: 12px;
	color: var(--n-text-color-3);
	word-break: break-all;
}
.kv-val {
	font-size: 13px;
	white-space: pre-wrap;
	word-break: break-word;
	font-family: var(--font-mono, ui-monospace, monospace);
	user-select: text;
}
</style>
