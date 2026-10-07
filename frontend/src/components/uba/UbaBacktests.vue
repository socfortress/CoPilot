<template>
	<UbaSection title="Backtest" test-id="uba-backtests">
		<template #description>
			Replays recent history through a separate copy of UBA's rules and reports what they would have
			found: per rule, how often, for whom, and the alerts it would have raised. Nothing is alerted or
			stored on entities. A warm-up replays older history first so baselines and learning periods exist.
		</template>

		<!-- Start a run: what to replay, then the button. -->
		<div class="panel border-default flex flex-col gap-3 rounded-lg border p-3" data-testid="uba-backtest-form">
			<span class="text-secondary flex items-center gap-1.5 text-xs font-medium">
				<Icon name="carbon:play-outline" :size="14" class="text-primary" />
				Run a backtest
			</span>
			<div class="flex flex-wrap items-end gap-3">
				<n-form-item label="Rules" :show-feedback="false" size="small" class="min-w-72 grow">
					<n-select
						v-model:value="rules"
						multiple
						filterable
						clearable
						max-tag-count="responsive"
						:options="ruleOptions"
						:loading="catalogLoading"
						placeholder="All rules"
					/>
				</n-form-item>
				<n-form-item label="Days" :show-feedback="false" size="small" class="w-28">
					<n-select v-model:value="days" :options="DAY_OPTIONS" />
				</n-form-item>
				<n-form-item label="Warm-up" :show-feedback="false" size="small" class="w-32">
					<n-select v-model:value="warmup" :options="WARMUP_OPTIONS" />
				</n-form-item>
				<n-form-item label="Filter (optional)" :show-feedback="false" size="small" class="min-w-60 grow">
					<n-input v-model:value="filter" clearable placeholder="e.g. data_win_system_eventID:(4720 OR 4726)" />
				</n-form-item>
				<n-button type="primary" size="small" :loading="starting" data-testid="uba-backtest-run" @click="start">
					<template #icon><Icon name="carbon:play" :size="14" /></template>
					Run backtest
				</n-button>
			</div>
		</div>

		<div class="flex items-baseline gap-2 pt-1">
			<span class="text-secondary text-xs font-medium">Runs</span>
			<span class="text-tertiary font-mono text-[11px]">{{ jobs.length }}</span>
		</div>
		<UbaError v-if="error" :error />
		<n-data-table
			v-else
			:columns
			:data="jobs"
			:loading
			:row-key="(row: UbaBacktest) => row.id"
			size="small"
			:scroll-x="820"
			class="uba-table"
			data-testid="uba-backtest-runs"
		/>

		<div v-if="selected" class="panel border-default flex flex-col gap-3 rounded-lg border p-3" data-testid="uba-backtest-result">
			<div class="flex flex-wrap items-center gap-2 text-sm">
				<b>Result</b>
				<span class="text-secondary text-xs">
					{{ formatDate(selected.result!.since, dFormats.datetime) }} –
					{{ formatDate(selected.result!.until, dFormats.datetime) }} ·
					{{ selected.result!.docs.toLocaleString() }} events scored
					<template v-if="selected.result!.warmup_docs">
						({{ selected.result!.warmup_docs.toLocaleString() }} warm-up)
					</template>
					· {{ selected.result!.alert_count }} alert(s) it would have raised
				</span>
				<n-button text size="tiny" class="ml-auto" @click="selected = null">Close</n-button>
			</div>
			<n-alert v-if="selected.result!.truncated" type="warning" :bordered="false" class="text-xs">
				Stopped at UBA's document limit: these numbers cover only the first part of the window. Use fewer
				days, a filter, or fewer rules.
			</n-alert>
			<n-data-table
				:columns="resultColumns"
				:data="selected.result!.rules"
				:row-key="(row: UbaBacktestRuleResult) => row.rule_id"
				size="small"
				:scroll-x="700"
			/>
			<p v-if="!selected.result!.rules.length" class="text-secondary text-sm">No rule found anything.</p>
			<div v-if="selected.result!.alerts.length" class="flex flex-col gap-1">
				<span class="text-secondary text-xs">Alerts it would have raised (first {{ selected.result!.alerts.length }})</span>
				<ul class="m-0 flex list-none flex-col gap-0.5 p-0 text-xs">
					<li v-for="(a, i) of selected.result!.alerts.slice(0, 20)" :key="i">
						<b>{{ a.entity }}</b>
						· risk {{ Math.round(a.risk) }} ·
						<span class="font-mono">{{ a.rules.join(", ") }}</span>
					</li>
				</ul>
			</div>
		</div>
	</UbaSection>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { UbaBacktest, UbaBacktestRuleResult, UbaBacktestStatus, UbaRuleInfo } from "@/types/uba"
import { NAlert, NButton, NDataTable, NFormItem, NInput, NPopover, NSelect, NTag, NTooltip, useMessage } from "naive-ui"
import { computed, onBeforeMount, onBeforeUnmount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils/format"
import UbaError from "./UbaError.vue"
import UbaSection from "./ui/UbaSection.vue"
import { requesterOrigin, shortError } from "./utils"

const { customerCode } = defineProps<{ customerCode: string }>()

const DAY_OPTIONS = [1, 3, 7].map(d => ({ label: `${d} day${d > 1 ? "s" : ""}`, value: d }))
const WARMUP_OPTIONS = [0, 7, 14].map(d => ({ label: d ? `${d} days` : "none", value: d }))
const POLL_MS = 5000
const ACTIVE: UbaBacktestStatus[] = ["queued", "running", "cancelling"]

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const catalog = ref<UbaRuleInfo[]>([])
const catalogLoading = ref(false)
const rules = ref<string[]>([])
const days = ref(1)
const warmup = ref(0)
const filter = ref("")
const starting = ref(false)
const loading = ref(false)
const error = ref<ApiError | null>(null)
const jobs = ref<UbaBacktest[]>([])
const selected = ref<UbaBacktest | null>(null)
let poll: ReturnType<typeof setInterval> | null = null

const ruleOptions = computed(() =>
	catalog.value
		.filter(r => r.enabled !== false)
		.map(r => ({ label: `${r.id} · ${r.name}`, value: r.id }))
		.sort((a, b) => a.value.localeCompare(b.value))
)

function statusType(status: UbaBacktestStatus) {
	return (
		{ queued: "default", running: "info", cancelling: "warning", done: "success", error: "error", cancelled: "default" } as const
	)[status]
}

/** How a run's status reads: an icon and a word, always with the colour. */
const STATUS_META: Record<UbaBacktestStatus, { icon: string; label: string }> = {
	queued: { icon: "carbon:time", label: "queued" },
	running: { icon: "carbon:in-progress", label: "running" },
	cancelling: { icon: "carbon:in-progress-warning", label: "cancelling" },
	done: { icon: "carbon:checkmark-filled", label: "done" },
	error: { icon: "carbon:warning-filled", label: "failed" },
	cancelled: { icon: "carbon:close-outline", label: "cancelled" }
}

/** "4 s", "2 min": how long a finished run took. */
function took(job: UbaBacktest): string | null {
	if (!job.started_at || !job.finished_at) return null
	const seconds = Math.max(0, dayjs(job.finished_at).diff(dayjs(job.started_at), "second"))
	return seconds < 90 ? `${seconds} s` : `${Math.round(seconds / 60)} min`
}

/** The second line under a run's status: what it is doing, how long it took, or what went wrong. */
function statusDetail(job: UbaBacktest) {
	if (job.status === "error" && job.error) {
		return (
			<div class="flex max-w-[420px] min-w-0 items-center gap-1.5">
				<span class="text-secondary min-w-0 truncate font-mono text-[11px]" title={shortError(job.error, 400)}>
					{shortError(job.error)}
				</span>
				<NPopover trigger="click" placement="bottom-end" style="max-width: 520px">
					{{
						trigger: () => (
							<NButton text size="tiny" class="shrink-0 text-[11px]" data-testid="uba-backtest-error-details">
								Details
							</NButton>
						),
						default: () => <pre class="m-0 font-mono text-[11px] leading-relaxed whitespace-pre-wrap">{job.error}</pre>
					}}
				</NPopover>
			</div>
		)
	}
	if ((job.status === "running" || job.status === "cancelling") && job.progress?.docs) {
		return (
			<span class="text-tertiary font-mono text-[11px] tabular-nums">
				{`${job.progress.docs.toLocaleString()} events${job.progress.phase ? ` · ${job.progress.phase}` : ""}`}
			</span>
		)
	}
	if (job.status === "done") {
		const duration = took(job)
		return duration ? <span class="text-tertiary font-mono text-[11px]">{`took ${duration}`}</span> : null
	}
	if (job.status === "queued") return <span class="text-tertiary text-[11px]">starts within about 30 s</span>
	return null
}

const columns: DataTableColumns<UbaBacktest> = [
	{
		title: "Requested",
		key: "created_at",
		width: 210,
		render: row => {
			const origin = requesterOrigin(row.requested_by)
			return (
				<div class="flex flex-col leading-tight">
					<span class="text-sm">{dayjs(row.created_at).fromNow()}</span>
					<span class="text-tertiary truncate text-[11px]">
						<span class="font-mono tabular-nums">{String(formatDate(row.created_at, dFormats.datetime))}</span>
						{origin.by ? ` · ${origin.by}` : ""}
						{origin.via ? ` via ${origin.via}` : ""}
					</span>
				</div>
			)
		}
	},
	{
		title: "Window",
		key: "params",
		minWidth: 260,
		render: row => {
			const p = row.params
			return (
				<div class="flex flex-wrap items-center gap-1.5">
					<span class="param-chip font-mono text-[11px]">{`${p.days} day${p.days === 1 ? "" : "s"}`}</span>
					{p.warmup_days ? <span class="param-chip font-mono text-[11px]">{`+${p.warmup_days} d warm-up`}</span> : null}
					{p.rules?.length ? (
						<NTooltip>
							{{
								trigger: () => (
									<span class="param-chip cursor-help font-mono text-[11px]">{`${p.rules?.length} rule${p.rules?.length === 1 ? "" : "s"}`}</span>
								),
								default: () => <span class="font-mono text-xs whitespace-pre-line">{p.rules?.join("\n")}</span>
							}}
						</NTooltip>
					) : (
						<span class="text-tertiary text-[11px]">all rules</span>
					)}
					{p.filter ? (
						<NTooltip>
							{{
								trigger: () => (
									<span class="param-chip flex cursor-help items-center gap-1 font-mono text-[11px]">
										<Icon name="carbon:filter" size={11} />
										filter
									</span>
								),
								default: () => <span class="font-mono text-xs">{p.filter}</span>
							}}
						</NTooltip>
					) : null}
				</div>
			)
		}
	},
	{
		title: "Status",
		key: "status",
		width: 280,
		render: row => (
			<div class="flex min-w-0 flex-col items-start gap-1">
				<NTag size="small" round type={statusType(row.status)} bordered={false}>
					{{
						icon: () => <Icon name={STATUS_META[row.status].icon} size={12} />,
						default: () => STATUS_META[row.status].label
					}}
				</NTag>
				{statusDetail(row)}
			</div>
		)
	},
	{
		title: "",
		key: "actions",
		width: 130,
		align: "right",
		render: row =>
			row.status === "done" ? (
				<NButton size="tiny" secondary onClick={() => view(row)}>
					{{ icon: () => <Icon name="carbon:view" size={13} />, default: () => "View result" }}
				</NButton>
			) : row.status === "queued" || row.status === "running" ? (
				<NButton size="tiny" quaternary onClick={() => cancel(row)}>
					{{ icon: () => <Icon name="carbon:stop-outline" size={13} />, default: () => "Cancel" }}
				</NButton>
			) : null
	}
]

const resultColumns: DataTableColumns<UbaBacktestRuleResult> = [
	{
		type: "expand",
		expandable: row => row.samples.length > 0 || row.top_entities.length > 0,
		renderExpand: row => (
			<div class="flex flex-col gap-2 py-1 text-xs">
				{row.top_entities.length ? (
					<div class="flex flex-wrap items-center gap-1.5">
						<span class="text-tertiary">Top entities</span>
						{row.top_entities.map(e => (
							<span class="param-chip font-mono text-[11px]">{`${e.entity} · ${e.signals}`}</span>
						))}
					</div>
				) : null}
				{row.samples.length ? (
					<ul class="m-0 flex list-none flex-col gap-0.5 p-0">
						{row.samples.map(sample => (
							<li class="text-secondary font-mono text-[11px]">{sample}</li>
						))}
					</ul>
				) : null}
			</div>
		)
	},
	{
		title: "Rule",
		key: "rule_id",
		minWidth: 240,
		render: row => <span class="rule-chip inline-block max-w-full truncate align-middle font-mono text-xs">{row.rule_id}</span>
	},
	{ title: "Findings", key: "signals", width: 100, align: "right", render: row => <span class="font-mono tabular-nums">{row.signals}</span> },
	{ title: "Per day", key: "per_day", width: 90, align: "right", render: row => <span class="font-mono tabular-nums">{row.per_day}</span> },
	{ title: "Entities", key: "entities", width: 90, align: "right", render: row => <span class="font-mono tabular-nums">{row.entities}</span> },
	{
		title: "Top entity",
		key: "top",
		minWidth: 200,
		ellipsis: { tooltip: true },
		render: row =>
			row.top_entities[0] ? (
				<span>
					{row.top_entities[0].entity}
					<span class="text-tertiary font-mono text-[11px]">{` · ${row.top_entities[0].signals}`}</span>
				</span>
			) : (
				<span class="text-tertiary">—</span>
			)
	}
]

function load(quiet = false) {
	if (!quiet) loading.value = true
	error.value = null
	Api.uba
		.getBacktests(customerCode)
		.then(res => {
			jobs.value = res.data.backtests
			const active = jobs.value.some(j => ACTIVE.includes(j.status))
			if (active && !poll) poll = setInterval(load, POLL_MS, true)
			if (!active && poll) {
				clearInterval(poll)
				poll = null
			}
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
}

function start() {
	starting.value = true
	Api.uba
		.createBacktest(customerCode, {
			days: days.value,
			warmup_days: warmup.value,
			rules: rules.value.length ? rules.value : undefined,
			filter: filter.value.trim() || undefined
		})
		.then(() => {
			message.success("Backtest queued: UBA starts it within about 30 seconds.")
			load(true)
		})
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "Queuing the backtest failed.")
		})
		.finally(() => {
			starting.value = false
		})
}

function view(job: UbaBacktest) {
	Api.uba
		.getBacktest(customerCode, job.id)
		.then(res => {
			selected.value = res.data.backtest.result ? res.data.backtest : null
		})
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "Loading the result failed.")
		})
}

function cancel(job: UbaBacktest) {
	Api.uba
		.cancelBacktest(customerCode, job.id)
		.then(() => load(true))
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "Cancelling failed.")
		})
}

function loadCatalog() {
	catalogLoading.value = true
	Api.uba
		.getRuleCatalog(customerCode)
		.then(res => {
			catalog.value = res.data.rules
		})
		.catch(() => {
			catalog.value = [] // the rule picker stays empty: "all rules" still works
		})
		.finally(() => {
			catalogLoading.value = false
		})
}

onBeforeMount(() => {
	load()
	loadCatalog()
})
onBeforeUnmount(() => {
	if (poll) clearInterval(poll)
})
</script>

<style scoped>
.panel {
	background-color: var(--bg-secondary-color);
}

/* JSX cells are not scoped: reach them through the table. */
:deep(.param-chip) {
	padding: 1px 6px;
	border-radius: 4px;
	background-color: var(--hover-color);
	white-space: nowrap;
}
</style>
