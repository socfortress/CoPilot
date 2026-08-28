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
			<n-form class="border-default flex flex-wrap items-end gap-3 border-b px-5 py-4">
				<n-form-item label="Customer" :show-feedback="false" class="min-w-55 grow">
					<n-select
						v-model:value="customerCode"
						:options="customerOptions"
						:loading="loadingCustomers"
						filterable
						placeholder="Select a customer"
					/>
				</n-form-item>
				<n-form-item label="Look-back" :show-feedback="false">
					<n-select
						v-model:value="rangeSeconds"
						:options="rangeOptions"
						class="w-30!"
						:consistent-menu-width="false"
					/>
				</n-form-item>
				<n-button type="primary" :loading="running" :disabled="!customerCode || running" @click="runBacktest">
					<template #icon><Icon :name="RunIcon" :size="16" /></template>
					Run backtest
				</n-button>
			</n-form>

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
					<div v-else-if="result" class="flex flex-col gap-8">
						<div class="flex flex-col gap-4">
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
						</div>

						<!-- headline stats -->
						<div class="stat-strip">
							<div v-for="(s, i) of statTiles" :key="i" class="stat">
								<span class="stat__label">
									<Icon :name="s.icon" :size="13" :style="{ color: s.color }" />
									{{ s.title }}
								</span>
								<span class="stat__value">{{ s.value }}</span>
							</div>
						</div>

						<!-- volume over time -->
						<section v-if="result.per_bucket.length" class="panel">
							<header class="panel__head">
								<Icon :name="ChartIcon" :size="15" class="panel__icon" />
								<h4 class="panel__title">
									Matches per {{ result.bucket_unit === "1h" ? "hour" : "day" }}
								</h4>
								<div class="panel__meta">
									<span>
										peak
										<b>{{ fmt(bucketPeak) }}</b>
									</span>
									<span class="panel__sep">·</span>
									<span>
										avg
										<b>{{ fmt(bucketAvg) }}</b>
									</span>
									<span class="panel__sep">·</span>
									<span>
										buckets
										<b>{{ result.per_bucket.length }}</b>
									</span>
								</div>
							</header>
							<div class="panel__body">
								<ChartColumn
									:labels="bucketLabels"
									:data="bucketData"
									height="260px"
									labels-datetime
									monochrome
								/>
							</div>
						</section>

						<!-- aggregation simulation -->
						<section
							v-if="result.mode === 'aggregation' && result.aggregation"
							class="panel panel--warning"
						>
							<header class="panel__head">
								<Icon :name="AlertIcon" :size="15" class="panel__icon panel__icon--warning" />
								<h4 class="panel__title">Threshold simulation</h4>
								<code class="panel__expr">
									{{ result.aggregation.function
									}}{{ result.aggregation.field ? `(${result.aggregation.field})` : "()" }}
									{{ result.aggregation.condition }} {{ result.aggregation.threshold }} /
									{{ result.aggregation.window }}
									<template v-if="result.aggregation.group_by.length">
										by {{ result.aggregation.group_by.join(", ") }}
									</template>
								</code>
							</header>

							<div class="panel__body flex flex-col gap-5">
								<!-- verdict figures -->
								<div class="figures">
									<div class="figure">
										<span class="figure__label">Would have fired</span>
										<span class="figure__value figure__value--warning">
											≈ {{ fmt(result.aggregation.estimated_alerts) }}
										</span>
										<span class="figure__hint">
											alert{{ result.aggregation.estimated_alerts === 1 ? "" : "s" }} in
											{{ rangeLabel }}
										</span>
									</div>
									<div class="figure">
										<span class="figure__label">Per day</span>
										<span class="figure__value">{{ result.aggregation.per_day_alerts }}</span>
										<span class="figure__hint">on average</span>
									</div>
								</div>

								<!-- top offenders -->
								<div v-if="result.aggregation.top_offenders.length" class="subsection">
									<h5 class="subsection__title">Top offenders</h5>
									<div class="flex flex-col gap-1.5">
										<div v-for="(o, i) of result.aggregation.top_offenders" :key="i" class="meter">
											<span class="meter__label" :title="o.group">{{ o.group }}</span>
											<div class="meter__track">
												<div
													class="meter__fill meter__fill--warning"
													:style="{ width: pct(o.windows_alerting, maxOffenderWindows) }"
												/>
											</div>
											<span class="meter__value">
												peak
												<b>{{ o.peak }}</b>
												<span class="panel__sep">·</span>
												{{ o.windows_alerting }}×
											</span>
										</div>
									</div>
								</div>

								<!-- threshold sensitivity -->
								<div v-if="result.aggregation.sensitivity.length" class="subsection">
									<h5 class="subsection__title">Threshold sensitivity</h5>
									<div class="flex flex-wrap gap-2">
										<div
											v-for="(s, i) of result.aggregation.sensitivity"
											:key="i"
											class="chip"
											:class="{ 'is-current': s.threshold === result.aggregation.threshold }"
										>
											<span class="chip__key">≥ {{ s.threshold }}</span>
											<span class="chip__value">{{ fmt(s.alerts) }}</span>
										</div>
									</div>
									<span class="subsection__hint">
										Alerts at each threshold — the highlighted one is the rule's current setting.
									</span>
								</div>
							</div>
						</section>

						<!-- top values -->
						<section v-if="topFieldEntries.length" class="flex flex-col gap-2">
							<h4 class="section-title">Top values (from sampled events)</h4>
							<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
								<div v-for="[field, values] of topFieldEntries" :key="field" class="panel">
									<header class="panel__head panel__head--compact">
										<Icon :name="FieldIcon" :size="13" class="panel__icon" />
										<code class="panel__field" :title="field">{{ field }}</code>
										<span class="panel__count">{{ values.length }}</span>
									</header>
									<div class="panel__body panel__body--compact">
										<div v-for="(v, i) of values" :key="i" class="meter">
											<span class="meter__label" :title="v.value">{{ v.value }}</span>
											<div class="meter__track">
												<div
													class="meter__fill"
													:style="{ width: pct(v.count, maxTopCount(values)) }"
												/>
											</div>
											<span class="meter__value meter__value--narrow">{{ fmt(v.count) }}</span>
										</div>
									</div>
								</div>
							</div>
						</section>

						<!-- samples -->
						<section v-if="result.samples.length" class="mb-4 flex flex-col gap-2">
							<div class="flex flex-wrap items-center gap-2">
								<h4 class="section-title">Sample events ({{ result.samples.length }})</h4>
								<span class="text-secondary text-xs">click a row to inspect the full log</span>
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
				<Icon :name="LogIcon" :size="20" />
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
	NForm,
	NFormItem,
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
import ChartColumn from "@/components/common/charts/ChartColumn.vue"
import Icon from "@/components/common/Icon.vue"
import { MOCK_LATENCY_MS, mockBacktest, USE_MOCK_BACKTEST } from "@/components/copilotSearches/mock-backtest"
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
const ChartIcon = "carbon:chart-column"
const FieldIcon = "carbon:data-vis-1"

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

// --- volume over time ---
const bucketLabels = computed(() => (result.value?.per_bucket || []).map(b => b.bucket))
const bucketData = computed(() => (result.value?.per_bucket || []).map(b => b.count))
const bucketPeak = computed(() => Math.max(0, ...bucketData.value))
const bucketAvg = computed(() => {
	const d = bucketData.value
	return d.length ? Math.round(d.reduce((acc, n) => acc + n, 0) / d.length) : 0
})

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
	// Dev fixture: a fully-populated result so every panel in this modal can be
	// reviewed at once. No real rule + tenant pair fills them all.
	if (USE_MOCK_BACKTEST) {
		// Resolved after a beat rather than synchronously: the fixture exists to review
		// this modal, and a mock that lands instantly is the one state the real run
		// never has — the running spinner would go unreviewed.
		await new Promise(resolve => setTimeout(resolve, MOCK_LATENCY_MS))
		result.value = mockBacktest(customerCode.value, rangeSeconds.value)
		running.value = false
		return
	}

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

<style scoped lang="scss">
/*
 * Headline figures as one segmented strip rather than four floating cards: the 1px grid
 * gaps let the container background show through as dividers, so the segments stay flush
 * and perfectly separated however the grid wraps.
 */
.stat-strip {
	display: grid;
	overflow: hidden;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 1px;
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius);
	background-color: var(--border-color);

	@media (min-width: 768px) {
		grid-template-columns: repeat(4, minmax(0, 1fr));
	}
}

.stat {
	display: flex;
	flex-direction: column;
	gap: 3px;
	padding: 11px 14px;
	background-color: var(--bg-default-color);
}

.stat__label {
	display: flex;
	align-items: center;
	gap: 6px;
	font-size: 10px;
	font-weight: 600;
	letter-spacing: 0.07em;
	text-transform: uppercase;
	white-space: nowrap;
	color: var(--fg-secondary-color);
}

.stat__value {
	font-family: var(--font-family-display);
	font-size: 22px;
	font-weight: 700;
	line-height: 1.15;
}

/*
 * Headings carry an accent tick and a fading rule. Plain muted uppercase read as just
 * another row of small text next to the mono labels underneath it.
 */
@mixin heading {
	display: flex;
	align-items: center;
	gap: 8px;
	font-size: 10px;
	font-weight: 700;
	letter-spacing: 0.1em;
	text-transform: uppercase;
	color: var(--fg-default-color);

	&::before {
		content: "";
		width: 2px;
		height: 11px;
		flex-shrink: 0;
		border-radius: 1px;
		background-color: var(--border-color);
	}

	&::after {
		content: "";
		height: 1px;
		flex-grow: 1;
		background: var(--border-color);
	}
}

.section-title {
	@include heading;
}

/*
 * Every result block is a panel: a titled strip over a bordered body. The stack used to be
 * flat sections separated only by whitespace, which read as one long undifferentiated column.
 */
.panel {
	display: flex;
	flex-direction: column;
	overflow: hidden;
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius);
	background-color: var(--bg-default-color);
}

.panel__head {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 8px;
	padding: 9px 12px;
	border-block-end: 1px solid var(--border-color);
	background-color: var(--bg-secondary-color);

	&--compact {
		padding: 7px 10px;
	}
}

.panel__icon {
	flex-shrink: 0;
	color: var(--fg-secondary-color);

	&--warning {
		color: var(--warning-color);
	}
}

.panel__title {
	font-size: 12px;
	font-weight: 600;
	letter-spacing: 0.02em;
}

.panel__meta {
	display: flex;
	align-items: center;
	gap: 6px;
	margin-inline-start: auto;
	font-family: var(--font-family-mono);
	font-size: 11px;
	color: var(--fg-secondary-color);

	b {
		font-weight: 600;
		color: var(--fg-default-color);
	}
}

.panel__sep {
	opacity: 0.4;
}

/* The rule expression the simulation is based on — reads as code, because it is. */
.panel__expr {
	margin-inline-start: auto;
	padding: 2px 8px;
	border-radius: var(--border-radius-small);
	background-color: rgba(var(--warning-color-rgb) / 0.12);
	font-family: var(--font-family-mono);
	font-size: 11px;
	color: var(--warning-color);
}

/* Card title for a top-values panel: the field name, in mono, with its value count. */
.panel__field {
	overflow: hidden;
	padding: 0;
	background: none;
	font-family: var(--font-family-mono);
	font-size: 11.5px;
	font-weight: 600;
	text-overflow: ellipsis;
	white-space: nowrap;
	color: var(--fg-default-color);
}

.panel__count {
	margin-inline-start: auto;
	padding: 1px 7px;
	padding-top: 3px;
	border-radius: 999px;
	background-color: rgba(var(--primary-color-rgb) / 0.14);
	font-family: var(--font-family-mono);
	font-size: 10px;
	font-weight: 600;
	color: var(--primary-color);
}

.panel__body {
	padding: 12px;

	&--compact {
		display: flex;
		flex-direction: column;
		gap: 6px;
		padding: 10px;
	}
}

.panel--warning {
	--heading-accent: var(--warning-color);

	border-color: rgba(var(--warning-color-rgb) / 0.35);

	.panel__head {
		background-color: rgba(var(--warning-color-rgb) / 0.08);
	}
}

/* --- threshold simulation --- */
.figures {
	display: flex;
	flex-wrap: wrap;
	gap: 10px;
}

.figure {
	display: flex;
	min-width: 150px;
	flex: 1 1 0;
	flex-direction: column;
	gap: 1px;
	padding: 10px 12px;
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius-small);
	background-color: var(--bg-secondary-color);
}

.figure__label {
	font-size: 10px;
	font-weight: 600;
	letter-spacing: 0.06em;
	text-transform: uppercase;
	color: var(--fg-secondary-color);
}

.figure__value {
	font-family: var(--font-family-display);
	font-size: 26px;
	font-weight: 700;
	line-height: 1.15;

	&--warning {
		color: var(--warning-color);
	}
}

.figure__hint {
	font-size: 11px;
	color: var(--fg-secondary-color);
}

.subsection {
	display: flex;
	flex-direction: column;
	gap: 7px;
}

.subsection__title {
	@include heading;
}

.subsection__hint {
	font-size: 11px;
	color: var(--fg-secondary-color);
}

/* --- shared label + bar + value row, used by offenders and top values --- */
.meter {
	display: flex;
	align-items: center;
	gap: 10px;
}

.meter__label {
	overflow: hidden;
	width: 40%;
	max-width: 260px;
	flex-shrink: 0;
	font-family: var(--font-family-mono);
	font-size: 11.5px;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.meter__track {
	overflow: hidden;
	height: 6px;
	flex-grow: 1;
	border-radius: 999px;
	background-color: rgba(var(--fg-secondary-color-rgb) / 0.16);
}

.meter__fill {
	height: 100%;
	border-radius: 999px;
	background-color: var(--primary-color);
	transition: width 0.3s var(--bezier-ease);

	&--warning {
		background-color: var(--warning-color);
	}
}

.meter__value {
	width: 96px;
	flex-shrink: 0;
	text-align: end;
	font-family: var(--font-family-mono);
	font-size: 11px;
	color: var(--fg-secondary-color);

	b {
		font-weight: 600;
		color: var(--fg-default-color);
	}

	&--narrow {
		width: 48px;
	}
}

/* --- sensitivity chips --- */
.chip {
	display: flex;
	min-width: 68px;
	flex-direction: column;
	align-items: center;
	gap: 1px;
	padding: 6px 10px;
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius-small);
	transition:
		border-color 0.15s var(--bezier-ease),
		background-color 0.15s var(--bezier-ease);

	&.is-current {
		border-color: var(--primary-color);
		background-color: rgba(var(--primary-color-rgb) / 0.1);
	}
}

.chip__key {
	font-family: var(--font-family-mono);
	font-size: 10px;
	color: var(--fg-secondary-color);
}

.chip__value {
	font-family: var(--font-family-display);
	font-size: 16px;
	font-weight: 700;
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
