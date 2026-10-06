<template>
	<UbaSection title="Backtest">
		<template #description>
			Replays recent history through a separate copy of UBA's rules and reports what they would have
			found: per rule, how often, for whom, and the alerts it would have raised. Nothing is alerted or
			stored on entities. A warm-up replays older history first so baselines and learning periods exist.
		</template>

		<div class="flex flex-wrap items-end gap-3">
			<n-form-item label="Rules" :show-feedback="false" class="min-w-72 grow">
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
			<n-form-item label="Days" :show-feedback="false" class="w-28">
				<n-select v-model:value="days" :options="DAY_OPTIONS" />
			</n-form-item>
			<n-form-item label="Warm-up" :show-feedback="false" class="w-32">
				<n-select v-model:value="warmup" :options="WARMUP_OPTIONS" />
			</n-form-item>
			<n-form-item label="Filter (optional)" :show-feedback="false" class="min-w-60 grow">
				<n-input v-model:value="filter" clearable placeholder="e.g. data_win_system_eventID:(4720 OR 4726)" />
			</n-form-item>
			<n-button type="primary" :loading="starting" @click="start">
				<template #icon><Icon name="carbon:play" :size="14" /></template>
				Run backtest
			</n-button>
		</div>

		<UbaError v-if="error" :error />
		<n-data-table
			v-else
			:columns
			:data="jobs"
			:loading
			:row-key="(row: UbaBacktest) => row.id"
			size="small"
			:scroll-x="760"
			class="uba-table"
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
import { NAlert, NButton, NDataTable, NFormItem, NInput, NSelect, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, onBeforeUnmount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import UbaError from "./UbaError.vue"
import UbaSection from "./ui/UbaSection.vue"

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

function windowLabel(job: UbaBacktest) {
	const p = job.params
	const scope = p.rules?.length ? `${p.rules.length} rule${p.rules.length > 1 ? "s" : ""}` : "all rules"
	return `${p.days} d${p.warmup_days ? ` + ${p.warmup_days} d warm-up` : ""} · ${scope}${p.filter ? " · filtered" : ""}`
}

const columns: DataTableColumns<UbaBacktest> = [
	{
		title: "Requested",
		key: "created_at",
		width: 210,
		render: row => (
			<div class="flex flex-col">
				<span>{formatDate(row.created_at, dFormats.datetime)}</span>
				<span class="text-tertiary text-xs">{row.requested_by ?? ""}</span>
			</div>
		)
	},
	{ title: "Window", key: "params", minWidth: 200, render: row => windowLabel(row) },
	{
		title: "Status",
		key: "status",
		width: 200,
		render: row => (
			<div class="flex flex-col gap-0.5">
				<NTag size="small" type={statusType(row.status)} bordered={false}>
					{row.status}
				</NTag>
				{row.progress?.docs && row.status !== "done" ? (
					<span class="text-tertiary text-xs">
						{`${row.progress.docs.toLocaleString()} events · ${row.progress.phase ?? ""}`}
					</span>
				) : null}
				{row.error ? <span class="text-error text-xs">{row.error}</span> : null}
			</div>
		)
	},
	{
		title: "",
		key: "actions",
		width: 110,
		render: row =>
			row.status === "done" ? (
				<NButton size="tiny" secondary onClick={() => view(row)}>
					View result
				</NButton>
			) : row.status === "queued" || row.status === "running" ? (
				<NButton size="tiny" secondary onClick={() => cancel(row)}>
					Cancel
				</NButton>
			) : null
	}
]

const resultColumns: DataTableColumns<UbaBacktestRuleResult> = [
	{
		type: "expand",
		expandable: row => row.samples.length > 0 || row.top_entities.length > 0,
		renderExpand: row => (
			<div class="flex flex-col gap-2 text-xs">
				<div>
					<span class="text-secondary">Top entities: </span>
					{row.top_entities.map(e => `${e.entity} (${e.signals})`).join(", ")}
				</div>
				<ul class="flex flex-col gap-0.5">
					{row.samples.map(s => (
						<li class="font-mono">{s}</li>
					))}
				</ul>
			</div>
		)
	},
	{ title: "Rule", key: "rule_id", minWidth: 220, render: row => <span class="font-mono text-xs">{row.rule_id}</span> },
	{ title: "Signals", key: "signals", width: 90 },
	{ title: "Per day", key: "per_day", width: 90 },
	{ title: "Entities", key: "entities", width: 90 },
	{
		title: "Top entity",
		key: "top",
		minWidth: 180,
		ellipsis: { tooltip: true },
		render: row => (row.top_entities[0] ? `${row.top_entities[0].entity} (${row.top_entities[0].signals})` : "")
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
</style>
