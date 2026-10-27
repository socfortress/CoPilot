<template>
	<section class="flex flex-col gap-3" aria-label="Ops findings" data-testid="talon-ops-findings">
		<OpsSummary
			:summary
			:loading="summaryLoading"
			:failure="summaryFailure"
			:severity="status === 'open' ? severity : null"
			:stale-only
			:customer
			:platform
			@severity="onSeverityChip"
			@stale="onStaleChip"
			@customer="onCustomerChip"
		/>
		<div class="flex flex-wrap items-end gap-3">
			<label class="flex flex-col gap-1">
				<span class="text-secondary text-xs">Job</span>
				<n-select
					v-model:value="job"
					:options="jobOptions"
					clearable
					placeholder="Every job"
					size="small"
					class="w-52!"
					data-testid="talon-ops-filter-job"
				/>
			</label>
			<label class="flex flex-col gap-1">
				<span class="text-secondary text-xs">Customer</span>
				<n-select
					v-model:value="customer"
					:options="customerOptions"
					:loading="customersLoading"
					:disabled="platform"
					clearable
					filterable
					placeholder="Every customer"
					size="small"
					class="w-60!"
					data-testid="talon-ops-filter-customer"
				/>
			</label>
			<label class="flex flex-col gap-1">
				<span class="text-secondary text-xs">Status</span>
				<n-select
					v-model:value="status"
					:options="statusOptions"
					clearable
					placeholder="Any status"
					size="small"
					class="w-40!"
					data-testid="talon-ops-filter-status"
				/>
			</label>
			<label class="flex flex-col gap-1">
				<span class="text-secondary text-xs">Severity</span>
				<n-select
					v-model:value="severity"
					:options="severityOptions"
					clearable
					placeholder="Any severity"
					size="small"
					class="w-36!"
					data-testid="talon-ops-filter-severity"
				/>
			</label>
			<label v-if="isAdmin" class="flex items-center gap-2 pb-1">
				<n-switch v-model:value="platform" size="small" data-testid="talon-ops-filter-platform" />
				<span class="text-secondary text-xs">Platform findings only</span>
			</label>
			<label class="flex flex-col gap-1">
				<span class="text-secondary text-xs">Sort by</span>
				<n-radio-group v-model:value="order" size="small" data-testid="talon-ops-order">
					<n-radio-button value="severity" data-testid="talon-ops-order-severity">Severity</n-radio-button>
					<n-radio-button value="recent" data-testid="talon-ops-order-recent">
						Recently changed
					</n-radio-button>
				</n-radio-group>
			</label>
			<label class="flex items-center gap-2 pb-1">
				<n-switch v-model:value="grouped" size="small" data-testid="talon-ops-group" />
				<span class="text-secondary text-xs">Group by customer</span>
			</label>
			<n-button
				size="small"
				secondary
				class="ml-auto"
				:loading="loading && !items.length"
				:disabled="loading"
				data-testid="talon-ops-refresh"
				@click="reload()"
			>
				<template #icon><Icon name="carbon:renew" :size="14" /></template>
				Refresh
			</n-button>
		</div>

		<!-- The stale marker's tooltip, for keyboard and screen-reader users (`aria-describedby`). -->
		<span :id="STALE_HELP_ID" class="sr-only" data-testid="talon-ops-stale-help">{{ STALE_TEXT }}</span>
		<OpsProblem v-if="problem" :state="problem" @retry="reload()" />
		<template v-else>
			<div
				v-if="staleOnly"
				class="text-secondary flex flex-wrap items-center gap-2 text-xs"
				data-testid="talon-ops-stale-only"
			>
				<Icon name="carbon:filter" :size="12" />
				Showing only the loaded findings their job couldn't measure lately ({{ shown.length }} of
				{{ items.length }} loaded). Talon can't filter on this: load more to see others.
				<n-button text size="tiny" data-testid="talon-ops-stale-only-clear" @click="staleOnly = false">
					Show all
				</n-button>
			</div>
			<OpsBulk :selected="selectedFindings" @done="afterBulk()" @clear="checked = []" />
			<n-data-table
				v-if="!grouped || !shown.length"
				:columns
				:data="shown"
				:loading="loading && !items.length"
				:row-key
				:row-props
				:checked-row-keys="checked"
				size="small"
				:bordered="false"
				data-testid="talon-ops-table"
				@update:checked-row-keys="(keys: DataTableRowKey[]) => setChecked(shown, keys)"
			>
				<template #empty>
					<p class="text-tertiary py-6 text-center text-sm" data-testid="talon-ops-empty">
						{{
							staleOnly
								? "None of the loaded findings is marked not measured."
								: status === "open"
									? "No open findings. Talon's ops jobs found nothing that needs attention."
									: "No findings match these filters."
						}}
					</p>
				</template>
			</n-data-table>
			<template v-else>
				<section
					v-for="group of groups"
					:key="group.key"
					:aria-label="`Findings of ${group.label}`"
					class="flex flex-col gap-1"
					:data-testid="`talon-ops-group-${group.key || 'platform'}`"
				>
					<h4 class="text-secondary flex items-center gap-2 text-xs font-semibold">
						<bdi data-testid="talon-ops-group-label">{{ group.label }}</bdi>
						<span class="text-tertiary font-normal">
							{{ group.items.length }} finding{{ group.items.length === 1 ? "" : "s" }}
						</span>
					</h4>
					<n-data-table
						:columns
						:data="group.items"
						:row-key
						:row-props
						:checked-row-keys="checked"
						size="small"
						:bordered="false"
						@update:checked-row-keys="(keys: DataTableRowKey[]) => setChecked(group.items, keys)"
					/>
				</section>
			</template>
			<p v-if="dropped" class="text-tertiary text-xs" data-testid="talon-ops-dropped">
				{{ dropped }} finding{{ dropped === 1 ? "" : "s" }} from Talon couldn't be shown (not one of your
				customers, or not readable).
			</p>
			<div v-if="nextCursor" class="flex justify-center">
				<n-button
					size="small"
					secondary
					:loading="loadingMore"
					:disabled="loadingMore"
					data-testid="talon-ops-more"
					@click="loadMore()"
				>
					Load more
				</n-button>
			</div>
			<n-alert v-if="moreFailure" type="error" :bordered="false" data-testid="talon-ops-more-error">
				<bdi>{{ moreFailure }}</bdi>
			</n-alert>
		</template>
	</section>
</template>

<script setup lang="ts">
// The findings table (`GET /talon/ops/findings`) under its summary strip (`GET /talon/ops/summary`,
// `OpsSummary.vue`): filters for job, customer, status (open by default), severity and, for an admin,
// platform findings; sorted by severity (the default) or most recently changed (`order`, each with its
// own cursor); optionally grouped under each customer ("Platform" for platform findings). Columns for
// the selection, severity, title (with a link out), customer, job, first and last seen and status, with
// "Not measured since <time>" on a stale finding (its job couldn't check it, so it can't clear); cursor
// paging ("Load more"). Every value is shown as text. A row opens the detail drawer (`open`). A filter
// change starts again from the first page, clears the selection and recounts the strip; an answer for
// an older filter is dropped. Selected rows can be acknowledged or muted together (`OpsBulk.vue`).
import type { DataTableColumns, DataTableRowKey } from "naive-ui"
import type { TalonOpsFailure } from "@/api/endpoints/talonOps"
import type {
	TalonOpsFinding,
	TalonOpsJob,
	TalonOpsOrder,
	TalonOpsQuery,
	TalonOpsSeverity,
	TalonOpsStatus,
	TalonOpsSummary,
	TalonOpsSummaryQuery
} from "@/types/talonOps"
import { NAlert, NButton, NDataTable, NRadioButton, NRadioGroup, NSelect, NSwitch, NTag, NTooltip } from "naive-ui"
import { computed, h, onBeforeUnmount, ref, watch } from "vue"
import { RouterLink } from "vue-router"
import Api from "@/api"
import { opsFailure } from "@/api/endpoints/talonOps"
import Icon from "@/components/common/Icon.vue"
import { useCustomerOptions } from "@/composables/useCustomerOptions"
import { formatTime } from "../health/health"
import {
	customerText,
	groupByCustomer,
	isSelectable,
	isStale,
	jobLabel,
	PAGE_SIZE,
	problemState,
	rowLink,
	SEVERITIES,
	severityInfo,
	STALE_TEXT,
	STATUSES,
	statusInfo
} from "./ops"
import OpsBulk from "./OpsBulk.vue"
import OpsProblem from "./OpsProblem.vue"
import OpsSummary from "./OpsSummary.vue"

const { jobs = [], isAdmin = false } = defineProps<{ jobs?: TalonOpsJob[]; isAdmin?: boolean }>()
const emit = defineEmits<{ (e: "open", finding: TalonOpsFinding): void }>()

const STALE_HELP_ID = "talon-ops-stale-help"

const { options: customerOptions, loading: customersLoading, load: loadCustomers } = useCustomerOptions()

const job = ref<string | null>(null)
const customer = ref<string | null>(null)
const status = ref<TalonOpsStatus | null>("open")
const severity = ref<TalonOpsSeverity | null>(null)
const platform = ref(false)
const order = ref<TalonOpsOrder>("severity")
const grouped = ref(false)
/** The stale chip: only the loaded rows a job couldn't measure (Talon has no such filter). */
const staleOnly = ref(false)
const checked = ref<DataTableRowKey[]>([])

const summary = ref<TalonOpsSummary | null>(null)
const summaryLoading = ref(false)
const summaryFailure = ref<TalonOpsFailure | null>(null)
let summaryController: AbortController | null = null

const items = ref<TalonOpsFinding[]>([])
const nextCursor = ref<string | null>(null)
const dropped = ref(0)
const loading = ref(false)
const loadingMore = ref(false)
const failure = ref<TalonOpsFailure | null>(null)
const moreFailure = ref<string | null>(null)
let controller: AbortController | null = null

const problem = computed(() => problemState(failure.value))
const titles = computed(() => Object.fromEntries(jobs.map(j => [j.name, j.title])))
const jobOptions = computed(() => jobs.map(j => ({ label: jobLabel(j.name, titles.value), value: j.name })))
const statusOptions = STATUSES.map(s => ({ label: s.label, value: s.value }))
const severityOptions = SEVERITIES.map(s => ({ label: s.label, value: s.value }))

const shown = computed(() => (staleOnly.value ? items.value.filter(isStale) : items.value))
const groups = computed(() => groupByCustomer(shown.value))
const selectedFindings = computed(() => {
	const keys = new Set(checked.value)
	return items.value.filter(f => keys.has(f.id))
})

function rowKey(row: TalonOpsFinding) {
	return row.id
}

/** One table's selection changed: the other tables' (grouped) keep theirs. */
function setChecked(rows: TalonOpsFinding[], keys: DataTableRowKey[]) {
	const mine = new Set(rows.map(f => f.id as DataTableRowKey))
	checked.value = [...checked.value.filter(k => !mine.has(k)), ...keys.filter(k => mine.has(k))]
}

function query(cursor: string | null): TalonOpsQuery {
	return {
		job: job.value,
		customer_code: platform.value ? null : customer.value,
		status: status.value,
		severity: severity.value,
		platform: platform.value,
		order: order.value,
		limit: PAGE_SIZE,
		cursor
	}
}

function summaryQuery(): TalonOpsSummaryQuery {
	return { job: job.value, customer_code: platform.value ? null : customer.value, platform: platform.value }
}

/** The strip's counts, for the same job, customer and platform filters as the table. */
async function loadSummary() {
	summaryController?.abort()
	const own = new AbortController()
	summaryController = own
	summaryLoading.value = true
	summaryFailure.value = null
	try {
		const { data } = await Api.talonOps.summary(summaryQuery(), own.signal)
		if (summaryController !== own) return
		summary.value = data
	} catch (err) {
		if (summaryController !== own || own.signal.aborted) return
		summary.value = null
		summaryFailure.value = opsFailure(err)
	} finally {
		if (summaryController === own) summaryLoading.value = false
	}
}

/** The table from its first page, and the strip with it. */
function reload() {
	loadSummary()
	return loadFindings()
}

async function loadFindings() {
	checked.value = []
	controller?.abort()
	const own = new AbortController()
	controller = own
	loading.value = true
	failure.value = null
	moreFailure.value = null
	try {
		const { data } = await Api.talonOps.listFindings(query(null), own.signal)
		if (controller !== own) return
		items.value = data.items
		nextCursor.value = data.next_cursor
		dropped.value = data.dropped ?? 0
	} catch (err) {
		if (controller !== own || own.signal.aborted) return
		items.value = []
		nextCursor.value = null
		failure.value = opsFailure(err)
	} finally {
		if (controller === own) loading.value = false
	}
}

async function loadMore() {
	if (!nextCursor.value || loadingMore.value) return
	const own = controller
	loadingMore.value = true
	moreFailure.value = null
	try {
		const { data } = await Api.talonOps.listFindings(query(nextCursor.value), own?.signal)
		if (controller !== own) return
		const seen = new Set(items.value.map(f => f.id))
		items.value = [...items.value, ...data.items.filter(f => !seen.has(f.id))]
		nextCursor.value = data.next_cursor
		dropped.value += data.dropped ?? 0
	} catch (err) {
		if (controller === own) moreFailure.value = opsFailure(err).detail
	} finally {
		loadingMore.value = false
	}
}

/** A finding the detail drawer changed: its row shows the new state. */
function replace(finding: TalonOpsFinding) {
	items.value = items.value.map(f => (f.id === finding.id ? finding : f))
}

/** A bulk action finished: the table and the strip, once. */
function afterBulk() {
	reload()
}

defineExpose({ reload, replace, reloadSummary: loadSummary })

function onSeverityChip(value: TalonOpsSeverity) {
	// The strip counts open findings: its chip shows those, and a second click clears it.
	if (status.value === "open" && severity.value === value) {
		severity.value = null
		return
	}
	status.value = "open"
	severity.value = value
}

function onStaleChip() {
	staleOnly.value = !staleOnly.value
	if (staleOnly.value) status.value = "open"
}

function onCustomerChip(code: string | null) {
	if (code === null) {
		// The platform row: only an admin gets one.
		if (isAdmin) platform.value = !platform.value
		return
	}
	if (platform.value) platform.value = false
	customer.value = customer.value === code ? null : code
}

function rowProps(row: TalonOpsFinding) {
	return {
		class: "cursor-pointer",
		"data-testid": `talon-ops-row-${row.id}`,
		onClick: (e?: MouseEvent) => {
			// The checkbox and the link out are their own actions, not "open the finding".
			const target = e?.target as HTMLElement | null | undefined
			if (target?.closest?.(".n-data-table-td--selection, a")) return
			emit("open", row)
		}
	}
}

function titleCell(row: TalonOpsFinding) {
	const title = h("bdi", row.title)
	const link = rowLink(row)
	if (!link) return title
	return h("span", { class: "inline-flex max-w-full items-center gap-1.5" }, [
		h("span", { class: "truncate" }, [title]),
		h(
			RouterLink,
			{
				to: link.to,
				class: "text-primary inline-flex shrink-0",
				title: link.label,
				"aria-label": link.label,
				"data-testid": `talon-ops-link-${row.id}`,
				onClick: (e: MouseEvent) => e.stopPropagation()
			},
			() => h(Icon, { name: "carbon:launch", size: 12 })
		)
	])
}

const columns: DataTableColumns<TalonOpsFinding> = [
	{ type: "selection", disabled: row => !isSelectable(row) },
	{
		title: "Severity",
		key: "severity",
		width: 100,
		render: row => {
			const info = severityInfo(row.severity)
			return h(NTag, { type: info.tag as "default", size: "small", bordered: false }, () => info.label)
		}
	},
	{ title: "Title", key: "title", render: titleCell },
	{ title: "Customer", key: "customer_code", width: 140, render: row => h("bdi", customerText(row.customer_code)) },
	{ title: "Job", key: "job", width: 180, render: row => jobLabel(row.job, titles.value) },
	{ title: "First seen", key: "first_seen", width: 130, render: row => formatTime(row.first_seen) },
	{ title: "Last seen", key: "last_seen", width: 130, render: row => formatTime(row.last_seen) },
	{
		title: "Status",
		key: "status",
		width: 190,
		render: row => {
			const info = statusInfo(row.status)
			const status = h("span", { class: "inline-flex items-center gap-1" }, [
				h(Icon, { name: info.icon, size: 14 }),
				info.label
			])
			// The job couldn't measure it: it stays as it was, and can't clear until a run measures it again.
			// Talon keeps `stale_since` on a resolved finding, where it no longer matters.
			if (!isStale(row)) return status
			const stale = h(NTooltip, null, {
				trigger: () =>
					h(
						"span",
						{
							class: "text-warning inline-flex items-center gap-1 text-xs",
							tabindex: 0,
							"aria-describedby": STALE_HELP_ID,
							"data-testid": `talon-ops-stale-${row.id}`
						},
						[
							h(Icon, { name: "carbon:warning-alt", size: 12 }),
							`Not measured since ${formatTime(row.stale_since)}`
						]
					),
				default: () => STALE_TEXT
			})
			return h("div", { class: "flex flex-col gap-0.5" }, [status, stale])
		}
	}
]

watch([job, customer, status, severity, platform, order], () => reload())
loadCustomers()
reload()
onBeforeUnmount(() => {
	controller?.abort()
	summaryController?.abort()
})
</script>
