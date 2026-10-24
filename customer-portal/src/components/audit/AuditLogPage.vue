<template>
	<div class="flex flex-col gap-6" data-testid="audit-page">
		<header class="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
			<div class="flex min-w-0 flex-col gap-1.5">
				<h1 class="font-display text-2xl leading-tight font-semibold tracking-tight text-balance">Audit log</h1>
				<p class="text-secondary max-w-prose text-sm">
					Who did what in your organization's portal: alerts and cases moved and commented on, reports, and
					your users' sign-ins and accounts. Your SOC's actions are shown as SOC.
				</p>
			</div>
			<n-button
				v-if="data"
				secondary
				:loading="exporting"
				:disabled="!data.total"
				data-testid="audit-export"
				@click="exportCsv()"
			>
				<template #icon><Icon name="carbon:download" :size="16" /></template>
				Export CSV
			</n-button>
		</header>

		<div
			v-if="forbidden"
			class="bg-default border-default flex flex-col items-center gap-2 rounded-lg border px-6 py-14 text-center"
			data-testid="audit-forbidden"
		>
			<Icon name="carbon:locked" :size="28" class="text-tertiary" />
			<p class="text-default font-semibold">The audit log is for your organization's administrators</p>
			<p class="text-secondary max-w-md text-sm">
				Your SOC decides who administers your organization and whether its audit log is shown. Ask your SOC
				contact if you need it.
			</p>
		</div>

		<template v-else>
			<div class="flex flex-wrap items-center gap-2" data-testid="audit-filters">
				<n-select
					:value="state.category"
					:options="categoryOptions"
					placeholder="All activity"
					clearable
					size="small"
					class="w-52!"
					data-testid="audit-filter-category"
					@update:value="(category: AuditCategory | null) => update({ category })"
				/>
				<n-select
					:value="state.userId"
					:options="userOptions"
					placeholder="Everyone"
					clearable
					filterable
					size="small"
					class="w-52!"
					data-testid="audit-filter-user"
					@update:value="(userId: number | null) => update({ userId })"
				/>
				<n-date-picker
					:value="state.from ? dayToTimestamp(state.from) : null"
					type="date"
					placeholder="From"
					:format="pickerFormat"
					:is-date-disabled="(ts: number) => !!state.to && timestampToDay(ts) > state.to"
					clearable
					size="small"
					class="w-36!"
					data-testid="audit-filter-from"
					@update:value="(ts: number | null) => update({ from: ts === null ? null : timestampToDay(ts) })"
				/>
				<n-date-picker
					:value="state.to ? dayToTimestamp(state.to) : null"
					type="date"
					placeholder="To"
					:format="pickerFormat"
					:is-date-disabled="(ts: number) => !!state.from && timestampToDay(ts) < state.from"
					clearable
					size="small"
					class="w-36!"
					data-testid="audit-filter-to"
					@update:value="(ts: number | null) => update({ to: ts === null ? null : timestampToDay(ts) })"
				/>
				<n-select
					v-if="customers.length > 1"
					:value="state.customer"
					:options="customerOptions"
					placeholder="All customers"
					clearable
					size="small"
					class="w-52!"
					data-testid="audit-filter-customer"
					@update:value="(customer: string | null) => update({ customer })"
				/>
				<n-button v-if="hasFilters(state)" size="small" quaternary data-testid="audit-clear" @click="clear()">
					Clear filters
				</n-button>
			</div>

			<PanelError
				v-if="error && !data"
				:message="error"
				class="bg-default border-default rounded-lg border"
				@retry="load()"
			/>

			<section
				v-else
				class="border-default bg-default @container overflow-hidden rounded-lg border"
				:aria-busy="loading || undefined"
			>
				<div v-if="!data" class="flex flex-col gap-3 p-3" data-testid="audit-loading">
					<n-skeleton v-for="n of 6" :key="n" :height="48" :sharp="false" class="rounded-md" />
				</div>

				<div
					v-else-if="!data.entries.length"
					class="flex flex-col items-center gap-2 px-6 py-14 text-center"
					data-testid="audit-empty"
				>
					<Icon name="carbon:catalog" :size="28" class="text-tertiary" />
					<p class="text-default font-semibold">
						{{ hasFilters(state) ? "Nothing matches these filters" : "Nothing recorded yet" }}
					</p>
					<p class="text-secondary max-w-md text-sm">{{ retentionText(data.retention_days) }}</p>
				</div>

				<ol
					v-else
					class="divide-border m-0 flex list-none flex-col divide-y p-0"
					:class="{ 'opacity-60': loading }"
				>
					<li
						v-for="entry of data.entries"
						:key="entry.id"
						class="flex gap-3 px-4 py-3"
						:data-action="entry.action"
						data-testid="audit-row"
					>
						<span
							class="bg-secondary text-secondary mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md"
							:title="CATEGORY_LABELS[entry.category]"
						>
							<Icon :name="CATEGORY_ICONS[entry.category]" :size="15" />
						</span>
						<div class="flex min-w-0 grow flex-col gap-1">
							<div class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-sm">
								<span class="text-default font-medium">{{ entry.label }}</span>
								<template v-if="entry.target">
									<!-- An alert or a case opens in its modal; its header leads to the page. -->
									<button
										v-if="targetEntity(entry)"
										type="button"
										class="text-primary min-w-0 cursor-pointer truncate border-0 bg-transparent p-0 text-left underline-offset-2 hover:underline focus-visible:underline"
										data-testid="audit-target"
										@click="openEntity(targetEntity(entry)!)"
									>
										<bdi>{{ targetLabel(entry.target) }}</bdi>
									</button>
									<RouterLink
										v-else-if="targetRoute(entry)"
										:to="targetRoute(entry)!"
										class="text-primary min-w-0 truncate"
										data-testid="audit-target"
									>
										<bdi>{{ targetLabel(entry.target) }}</bdi>
									</RouterLink>
									<span v-else class="text-secondary min-w-0 truncate" data-testid="audit-target">
										<bdi>{{ targetLabel(entry.target) }}</bdi>
									</span>
								</template>
								<span
									v-if="changeLabel(entry)"
									class="text-secondary font-mono text-xs"
									data-testid="audit-change"
								>
									{{ changeLabel(entry) }}
								</span>
								<n-tag
									v-if="entry.result === 'failure'"
									type="error"
									size="tiny"
									:bordered="false"
									data-testid="audit-failure"
								>
									Failed
								</n-tag>
							</div>
							<div class="text-tertiary flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
								<span class="flex items-center gap-1.5" data-testid="audit-actor">
									<Icon :name="entry.actor.kind === 'soc' ? 'carbon:security' : 'carbon:user'" :size="12" />
									<bdi :class="{ 'text-secondary font-medium': entry.actor.kind !== 'unknown' }">
										{{ actorLabel(entry.actor) }}
									</bdi>
								</span>
								<time :datetime="entry.timestamp" class="tabular-nums">
									{{ formatDate(entry.timestamp, dFormats.datetimesec, { tz: true }) }}
								</time>
								<span v-if="customers.length > 1 && entry.customer_code" data-testid="audit-customer">
									<bdi>{{ customerName(entry.customer_code) }}</bdi>
								</span>
								<span v-if="entry.source_ip" class="font-mono" data-testid="audit-ip">
									{{ entry.source_ip }}
								</span>
							</div>
						</div>
					</li>
				</ol>

				<footer
					v-if="data && data.entries.length"
					class="border-default flex flex-wrap items-center justify-between gap-3 border-t px-4 py-3"
				>
					<span class="text-tertiary text-xs" data-testid="audit-total">
						{{ data.total }} {{ data.total === 1 ? "entry" : "entries" }} ·
						{{ retentionText(data.retention_days) }}
					</span>
					<n-pagination
						v-if="pageCount > 1"
						:page="state.page"
						:page-count
						:page-slot="6"
						size="small"
						data-testid="audit-pagination"
						@update:page="(page: number) => go({ ...state, page })"
					/>
				</footer>
			</section>
		</template>

		<!-- One modal for the page: the alert or case a target names; its header leads to the page. -->
		<EntityDetailsModal
			v-if="opened"
			v-model:show="entityShown"
			:title="opened.type === 'alert' ? 'Alert Details' : 'Case Details'"
			:entity="opened.type"
			:route="opened.type === 'alert' ? routeAlertDetails(opened.id) : routeCaseDetails(opened.id)"
		>
			<!-- What is changed in the modal is audited too: read the log again. -->
			<AlertDetails v-if="opened.type === 'alert'" :key="`alert-${opened.id}`" :alert-id="opened.id" @status-updated="load()" />
			<CaseDetails v-else :key="`case-${opened.id}`" :case-id="opened.id" @status-updated="load()" />
		</EntityDetailsModal>
	</div>
</template>

<script setup lang="ts">
import type { AuditEntityRef, AuditState } from "./auditLog"
import type { AuditCategory, AuditLog } from "@/types/audit"
import type { ApiError } from "@/types/common"
import { saveAs } from "file-saver"
import { NButton, NDatePicker, NPagination, NSelect, NSkeleton, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import { RouterLink, useRoute, useRouter } from "vue-router"
import Api from "@/api"
import AlertDetails from "@/components/alerts/AlertDetails"
import { dayToTimestamp, timestampToDay } from "@/components/alerts/filters/alertsFilters"
import CaseDetails from "@/components/cases/CaseDetails"
import EntityDetailsModal from "@/components/common/EntityDetailsModal.vue"
import Icon from "@/components/common/Icon.vue"
import PanelError from "@/components/overview/shared/PanelError.vue"
import { useAuditAvailability } from "@/composables/common/useAuditAvailability"
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { useNavigation } from "@/composables/common/useNavigation"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import {
	actorLabel,
	CATEGORIES,
	CATEGORY_ICONS,
	CATEGORY_LABELS,
	changeLabel,
	EMPTY_STATE,
	exportFilename,
	hasFilters,
	PAGE_SIZE,
	retentionText,
	stateFromQuery,
	stateToQuery,
	targetEntity,
	targetLabel,
	targetRoute,
	withFilter,
	withState
} from "./auditLog"

/**
 * A customer admin's Audit Log page (#1298): who did what in their organization, newest first.
 * The filters and the page live in the URL (`auditLog.ts`). What may be shown is the API's call:
 * the SOC arrives as "SOC" and the page has nothing else to show.
 */

const route = useRoute()
const router = useRouter()
const message = useMessage()
const settings = useSettingsStore()
const dFormats = settings.dateFormat
const pickerFormat = computed(() => dFormats.date.replace("DD", "dd").replace("YYYY", "yyyy"))
const { customers, check } = useAuditAvailability()

const data = ref<AuditLog | null>(null)
const error = ref<string | null>(null)
const forbidden = ref(false)
const exporting = ref(false)
const { loading, run } = useLatestRequest()

const state = computed(() => stateFromQuery(route.query))
const pageCount = computed(() => (data.value ? Math.max(1, Math.ceil(data.value.total / PAGE_SIZE)) : 1))
const customerCodes = computed(() => (state.value.customer ? [state.value.customer] : undefined))

const categoryOptions = CATEGORIES.map(category => ({ label: CATEGORY_LABELS[category], value: category }))
const userOptions = computed(() => (data.value?.members ?? []).map(member => ({ label: member.username, value: member.id })))
const customerOptions = computed(() =>
	customers.value.map(customer => ({ label: customer.customer_name, value: customer.customer_code }))
)

const { routeAlertDetails, routeCaseDetails } = useNavigation()
const opened = ref<AuditEntityRef | null>(null)
const entityShown = ref(false)

function openEntity(entity: AuditEntityRef) {
	opened.value = entity
	entityShown.value = true
}

function customerName(code: string) {
	return customers.value.find(customer => customer.customer_code === code)?.customer_name ?? code
}

function go(next: AuditState) {
	router.replace({ query: withState(route.query, next) })
}

function update(change: Partial<Omit<AuditState, "page">>) {
	go(withFilter(state.value, change))
}

function clear() {
	go(EMPTY_STATE)
}

function load() {
	error.value = null
	const query = stateToQuery(state.value)
	const codes = customerCodes.value
	return run(
		async signal => {
			const response = await Api.audit.getLog(query, codes, signal)
			if (signal.aborted) return
			data.value = response.data
			forbidden.value = false
		},
		err => {
			const status = (err as ApiError).response?.status
			if (status === 403) forbidden.value = true
			else if (status === 404 && state.value.userId) update({ userId: null })
			else error.value = getApiErrorMessage(err as ApiError) || "Could not load the audit log."
		}
	)
}

async function exportCsv() {
	exporting.value = true
	try {
		const response = await Api.audit.exportLog(stateToQuery(state.value), customerCodes.value)
		saveAs(response.data, exportFilename())
		if (response.headers?.["x-export-truncated"] === "true") {
			message.warning("The CSV holds the newest 10,000 entries: narrow the period for the rest.")
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Could not export the audit log.")
	} finally {
		exporting.value = false
	}
}

watch(
	() => JSON.stringify(state.value),
	() => {
		load()
	}
)

onBeforeMount(() => {
	check()
	load()
})
</script>
