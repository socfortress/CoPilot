<template>
	<div class="flex flex-col gap-3 pt-2" data-testid="cloud-findings">
		<div class="flex flex-wrap items-center gap-2">
			<n-select
				v-model:value="severity"
				:options="severityOptions"
				multiple
				clearable
				max-tag-count="responsive"
				placeholder="Every severity"
				class="w-60!"
				aria-label="Severity"
			/>
			<n-select v-model:value="status" :options="STATUS_OPTIONS" clearable placeholder="Failing and manual" class="w-44!" aria-label="Status" />
			<n-select v-model:value="muted" :options="MUTED_OPTIONS" class="w-40!" aria-label="Muted" />
			<n-checkbox v-if="compared" v-model:checked="newOnly">New since the scan before</n-checkbox>
			<n-input v-model:value="query" clearable placeholder="Search resources, checks, details" class="w-72!" aria-label="Search findings">
				<template #prefix><Icon :name="SearchIcon" :size="14" /></template>
			</n-input>
		</div>
		<div v-if="checkId" class="flex items-center gap-2 text-sm" data-testid="cloud-findings-check">
			<span class="text-secondary">Check</span>
			<n-tag closable size="small" :bordered="false" @close="emit('clearCheck')">
				<span class="font-mono">{{ checkId }}</span>
			</n-tag>
		</div>

		<n-alert v-if="error" type="error" :bordered="false">{{ errorText }}</n-alert>

		<section class="border-default bg-default overflow-hidden rounded-lg border" :aria-busy="loading">
			<header class="bg-secondary border-default flex flex-wrap items-baseline justify-between gap-2 border-b px-4 py-2">
				<span :class="SECTION_LABEL">Findings</span>
				<span class="text-secondary text-2xs font-mono tabular-nums">{{ total }} matching</span>
			</header>
			<div v-if="loading && !findings.length" class="flex flex-col gap-2 p-3">
				<n-skeleton v-for="n of 4" :key="n" :height="44" :sharp="false" class="rounded-md" />
			</div>
			<n-empty v-else-if="!findings.length" description="No finding matches" class="py-10" />
			<div v-else class="divide-border flex flex-col divide-y">
				<div v-for="finding of findings" :key="finding.id" :data-testid="`cloud-finding-${finding.id}`">
					<button
						type="button"
						class="hover:bg-secondary/50 grid w-full grid-cols-[auto_minmax(0,1fr)] items-start gap-x-3 gap-y-1 px-4 py-2.5 text-left transition-colors md:grid-cols-[6rem_minmax(0,1.4fr)_minmax(0,1.6fr)_7rem]"
						:aria-expanded="expanded === finding.id"
						@click="expanded = expanded === finding.id ? null : finding.id"
					>
						<span class="flex flex-wrap gap-1">
							<n-tag :type="SEVERITY_TAGS[finding.severity]" size="tiny" round :bordered="false">
								{{ SEVERITY_LABELS[finding.severity] }}
							</n-tag>
						</span>
						<span class="flex min-w-0 flex-col">
							<span class="text-default truncate text-sm" :title="finding.check_title ?? finding.check_id">
								<bdi>{{ finding.check_title ?? finding.check_id }}</bdi>
							</span>
							<span class="text-tertiary truncate font-mono text-xs">{{ finding.check_id }}</span>
						</span>
						<span class="col-span-2 flex min-w-0 flex-col md:col-span-1">
							<span class="text-default truncate text-sm" :title="finding.resource_name">
								<bdi>{{ finding.resource_name || "—" }}</bdi>
							</span>
							<span class="text-tertiary truncate font-mono text-xs" :title="finding.resource_uid">
								<bdi>{{ finding.resource_uid }}</bdi>
							</span>
						</span>
						<span class="col-span-2 flex flex-wrap items-center gap-1 md:col-span-1 md:justify-end">
							<n-tag v-if="finding.status === 'MANUAL'" size="tiny" type="warning" round :bordered="false">manual</n-tag>
							<n-tag v-if="finding.is_new" size="tiny" type="error" round :bordered="false">new</n-tag>
							<n-tag v-if="finding.muted" size="tiny" round :bordered="false">muted</n-tag>
							<span class="text-tertiary font-mono text-xs">{{ finding.region || "global" }}</span>
						</span>
					</button>
					<!-- The finding's own words come from the customer's cloud: text only, never markup. -->
					<dl
						v-if="expanded === finding.id"
						class="bg-secondary/40 border-default m-0 grid grid-cols-1 gap-x-6 gap-y-2 border-t px-4 py-3 text-sm md:grid-cols-[9rem_minmax(0,1fr)]"
						data-testid="cloud-finding-detail"
					>
						<dt class="text-tertiary text-xs">Detail</dt>
						<dd class="text-default m-0 whitespace-pre-wrap"><bdi>{{ finding.status_extended || "—" }}</bdi></dd>
						<dt class="text-tertiary text-xs">Resource</dt>
						<dd class="m-0 font-mono text-xs break-all"><bdi>{{ finding.resource_uid || "—" }}</bdi></dd>
						<dt class="text-tertiary text-xs">Type · service</dt>
						<dd class="m-0 text-xs">{{ finding.resource_type || "—" }} · {{ finding.service || "—" }}</dd>
						<dt class="text-tertiary text-xs">Cloud account</dt>
						<dd class="m-0 font-mono text-xs">
							{{ finding.cloud_account_uid || "—" }}
							<template v-if="finding.cloud_account_name">(<bdi>{{ finding.cloud_account_name }}</bdi>)</template>
						</dd>
						<template v-if="finding.resource_tags.length">
							<dt class="text-tertiary text-xs">Tags</dt>
							<dd class="m-0 flex flex-wrap gap-1">
								<n-tag v-for="tag of finding.resource_tags" :key="tag" size="tiny" :bordered="false">
									<bdi>{{ tag }}</bdi>
								</n-tag>
							</dd>
						</template>
						<dt class="text-tertiary text-xs">First seen</dt>
						<dd class="m-0 text-xs">
							{{ finding.first_seen_at ? formatDate(finding.first_seen_at, dFormats.datetime) : "—" }}
							<span v-if="finding.is_new" class="text-tertiary">(new in this scan)</span>
						</dd>
						<dt class="text-tertiary text-xs">Finding id</dt>
						<dd class="m-0 font-mono text-xs break-all"><bdi>{{ finding.finding_uid }}</bdi></dd>
					</dl>
				</div>
			</div>
			<div v-if="total > PAGE_SIZE" class="border-default flex justify-end border-t px-4 py-2">
				<n-pagination v-model:page="page" :page-size="PAGE_SIZE" :item-count="total" />
			</div>
		</section>
	</div>
</template>

<script setup lang="ts">
import type { CloudFinding, CloudFindingsQuery, CloudFindingStatus, CloudSeverity } from "@/types/cloud-assessment"
import type { ApiError } from "@/types/common"
import { refDebounced } from "@vueuse/core"
import { NAlert, NCheckbox, NEmpty, NInput, NPagination, NSelect, NSkeleton, NTag } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import { SEVERITIES, SEVERITY_LABELS, SEVERITY_TAGS } from "./utils"

const {
	customerCode,
	scanId,
	checkId = null,
	compared = true
} = defineProps<{
	customerCode: string
	scanId: number
	checkId?: string | null
	/** False for an account's first scan: nothing is new, since nothing came before. */
	compared?: boolean
}>()
const emit = defineEmits<{ (e: "clearCheck"): void }>()

const PAGE_SIZE = 50
const SearchIcon = "carbon:search"
const STATUS_OPTIONS = [
	{ label: "Failing", value: "FAIL" },
	{ label: "Manual review", value: "MANUAL" }
]
const MUTED_OPTIONS = [
	{ label: "Not muted", value: "unmuted" },
	{ label: "Muted only", value: "muted" },
	{ label: "Muted or not", value: "all" }
]
const severityOptions = SEVERITIES.map(value => ({ label: SEVERITY_LABELS[value], value }))
const dFormats = useSettingsStore().dateFormat

const severity = ref<CloudSeverity[]>([])
const status = ref<CloudFindingStatus | null>(null)
const muted = ref<"unmuted" | "muted" | "all">("unmuted")
const newOnly = ref(false)
const query = ref("")
const debouncedQuery = refDebounced(query, 300)
const page = ref(1)
const loading = ref(false)
const error = ref<ApiError | null>(null)
const findings = ref<CloudFinding[]>([])
const total = ref(0)
const expanded = ref<number | null>(null)
let controller: AbortController | null = null

const errorText = computed(() => (error.value ? getApiErrorMessage(error.value) || "The findings couldn't be read." : ""))

function params(): CloudFindingsQuery {
	return {
		severity: severity.value.length ? severity.value : undefined,
		status: status.value ?? undefined,
		muted: muted.value === "all" ? undefined : muted.value === "muted",
		new: newOnly.value || undefined,
		check_id: checkId ?? undefined,
		q: debouncedQuery.value.trim() || undefined,
		page: page.value,
		page_size: PAGE_SIZE
	}
}

function load() {
	controller?.abort()
	const current = new AbortController()
	controller = current
	loading.value = true
	error.value = null
	Api.cloudAssessment
		.getFindings(customerCode, scanId, params(), current.signal)
		.then(res => {
			findings.value = res.data.findings
			total.value = res.data.total
		})
		.catch((err: ApiError) => {
			if (!current.signal.aborted) error.value = err
		})
		.finally(() => {
			if (controller === current) loading.value = false
		})
}

// Any filter change starts again from page 1; a page change keeps the filters.
watch([severity, status, muted, newOnly, debouncedQuery, () => checkId], () => {
	expanded.value = null
	if (page.value !== 1) page.value = 1
	else load()
})
watch(page, () => {
	expanded.value = null
	load()
})

load()
</script>
