<template>
	<section class="flex flex-col gap-3" aria-label="Ops findings" data-testid="talon-ops-findings">
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

		<OpsProblem v-if="problem" :state="problem" @retry="reload()" />
		<template v-else>
			<n-data-table
				:columns
				:data="items"
				:loading="loading && !items.length"
				:row-key="(row: TalonOpsFinding) => row.id"
				:row-props
				size="small"
				:bordered="false"
				data-testid="talon-ops-table"
			>
				<template #empty>
					<p class="text-tertiary py-6 text-center text-sm" data-testid="talon-ops-empty">
						{{
							status === "open"
								? "No open findings. Talon's ops jobs found nothing that needs attention."
								: "No findings match these filters."
						}}
					</p>
				</template>
			</n-data-table>
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
// The findings table (`GET /talon/ops/findings`): filters for job, customer, status (open by default),
// severity and, for an admin, platform findings; columns for severity, title, customer, job, first
// and last seen and status; cursor paging ("Load more"). Every value is shown as text. A row opens
// the detail drawer (`open`). A filter change starts again from the first page; an answer for an
// older filter is dropped.
import type { DataTableColumns } from "naive-ui"
import type { TalonOpsFailure } from "@/api/endpoints/talonOps"
import type { TalonOpsFinding, TalonOpsJob, TalonOpsQuery, TalonOpsSeverity, TalonOpsStatus } from "@/types/talonOps"
import { NAlert, NButton, NDataTable, NSelect, NSwitch, NTag } from "naive-ui"
import { computed, h, onBeforeUnmount, ref, watch } from "vue"
import Api from "@/api"
import { opsFailure } from "@/api/endpoints/talonOps"
import Icon from "@/components/common/Icon.vue"
import { useCustomerOptions } from "@/composables/useCustomerOptions"
import { formatTime } from "../health/health"
import { customerText, jobLabel, PAGE_SIZE, problemState, SEVERITIES, severityInfo, STATUSES, statusInfo } from "./ops"
import OpsProblem from "./OpsProblem.vue"

const { jobs = [], isAdmin = false } = defineProps<{ jobs?: TalonOpsJob[]; isAdmin?: boolean }>()
const emit = defineEmits<{ (e: "open", finding: TalonOpsFinding): void }>()

const { options: customerOptions, loading: customersLoading, load: loadCustomers } = useCustomerOptions()

const job = ref<string | null>(null)
const customer = ref<string | null>(null)
const status = ref<TalonOpsStatus | null>("open")
const severity = ref<TalonOpsSeverity | null>(null)
const platform = ref(false)

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

function query(cursor: string | null): TalonOpsQuery {
	return {
		job: job.value,
		customer_code: platform.value ? null : customer.value,
		status: status.value,
		severity: severity.value,
		platform: platform.value,
		limit: PAGE_SIZE,
		cursor
	}
}

async function reload() {
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

defineExpose({ reload, replace })

function rowProps(row: TalonOpsFinding) {
	return {
		class: "cursor-pointer",
		"data-testid": `talon-ops-row-${row.id}`,
		onClick: () => emit("open", row)
	}
}

const columns: DataTableColumns<TalonOpsFinding> = [
	{
		title: "Severity",
		key: "severity",
		width: 100,
		render: row => {
			const info = severityInfo(row.severity)
			return h(NTag, { type: info.tag as "default", size: "small", bordered: false }, () => info.label)
		}
	},
	{ title: "Title", key: "title", ellipsis: { tooltip: true }, render: row => h("bdi", row.title) },
	{ title: "Customer", key: "customer_code", width: 140, render: row => h("bdi", customerText(row.customer_code)) },
	{ title: "Job", key: "job", width: 180, render: row => jobLabel(row.job, titles.value) },
	{ title: "First seen", key: "first_seen", width: 130, render: row => formatTime(row.first_seen) },
	{ title: "Last seen", key: "last_seen", width: 130, render: row => formatTime(row.last_seen) },
	{
		title: "Status",
		key: "status",
		width: 140,
		render: row => {
			const info = statusInfo(row.status)
			return h("span", { class: "inline-flex items-center gap-1" }, [
				h(Icon, { name: info.icon, size: 14 }),
				info.label
			])
		}
	}
]

watch([job, customer, status, severity, platform], () => reload())
loadCustomers()
reload()
onBeforeUnmount(() => controller?.abort())
</script>
