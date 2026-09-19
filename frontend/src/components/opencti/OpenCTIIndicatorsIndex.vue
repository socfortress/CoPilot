<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-wrap items-end gap-3">
			<n-form-item label="Search" :show-feedback="false" class="min-w-60 grow">
				<n-input
					v-model:value="search"
					placeholder="Whole words, e.g. sdk.netnut.io — press Enter"
					clearable
					@keydown.enter="reload()"
					@clear="clearSearch()"
				/>
			</n-form-item>
			<n-form-item label="Observable type" :show-feedback="false" class="w-48">
				<n-select v-model:value="observableType" :options="observableTypeOptions" clearable placeholder="Any" />
			</n-form-item>
			<n-form-item label="Min score" :show-feedback="false" class="w-32">
				<n-input-number v-model:value="minScore" :min="0" :max="100" clearable placeholder="Any" />
			</n-form-item>
			<n-button type="primary" :loading="loading && !indicators.length" @click="reload()">Search</n-button>
		</div>

		<div v-if="error" class="bg-secondary border-error rounded-lg border px-4 py-2.5">{{ error }}</div>

		<template v-else>
			<n-data-table
				:columns
				:data="indicators"
				:loading
				:row-key="(row: OpenCTIIndicator) => row.id"
				:row-props
				size="small"
				:scroll-x="1100"
				class="opencti-indicators-table"
			/>

			<div class="flex flex-wrap items-center justify-between gap-3">
				<span class="text-secondary text-sm">
					<template v-if="pageInfo?.global_count !== null && pageInfo?.global_count !== undefined">
						{{ indicators.length.toLocaleString() }} of
						{{ pageInfo.global_count.toLocaleString() }} indicators
					</template>
				</span>
				<n-button v-if="pageInfo?.has_next_page" secondary :loading @click="loadMore()">Load more</n-button>
			</div>
		</template>

		<n-drawer v-model:show="showDetail" :width="640" class="max-w-[95vw]" placement="right">
			<n-drawer-content title="OpenCTI entity" closable :native-scrollbar="false">
				<OpenCTIEntityDetail v-if="selectedId" :entity-id="selectedId" />
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns, SelectOption } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { OpenCTIIndicator, OpenCTIPageInfo } from "@/types/opencti"
import axios from "axios"
import { NButton, NDataTable, NDrawer, NDrawerContent, NFormItem, NInput, NInputNumber, NSelect, NTag } from "naive-ui"
import { onBeforeMount, ref, watch } from "vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils/format"
// TEMP(mock): UI/UX review — restore `import Api from "@/api"` and `Api.opencti` before merging.
import mockOpenCTI from "./__mock__/opencti-mock"
import OpenCTIEntityDetail from "./OpenCTIEntityDetail.vue"
import { scoreTagType } from "./utils"

const PAGE_SIZE = 25

// OpenCTI entity-type names; `StixFile` is how file hashes are stored.
const observableTypeOptions: SelectOption[] = [
	{ label: "IPv4 address", value: "IPv4-Addr" },
	{ label: "IPv6 address", value: "IPv6-Addr" },
	{ label: "Domain name", value: "Domain-Name" },
	{ label: "Hostname", value: "Hostname" },
	{ label: "URL", value: "Url" },
	{ label: "File (hash)", value: "StixFile" },
	{ label: "Email address", value: "Email-Addr" }
]

const dFormats = useSettingsStore().dateFormat
const search = ref("")
const observableType = ref<string | null>(null)
const minScore = ref<number | null>(null)
const indicators = ref<OpenCTIIndicator[]>([])
const pageInfo = ref<OpenCTIPageInfo | null>(null)
const loading = ref(false)
const error = ref("")
const showDetail = ref(false)
const selectedId = ref<string | null>(null)

let controller: AbortController | null = null

function fetchPage(append: boolean) {
	controller?.abort()
	const current = new AbortController()
	controller = current
	loading.value = true
	error.value = ""

	mockOpenCTI
		.getIndicators(
			{
				search: search.value.trim() || undefined,
				main_observable_type: observableType.value || undefined,
				min_score: minScore.value ?? undefined,
				first: PAGE_SIZE,
				after: append ? pageInfo.value?.end_cursor || undefined : undefined
			},
			current.signal
		)
		.then(res => {
			indicators.value = append ? [...indicators.value, ...res.data.indicators] : res.data.indicators
			pageInfo.value = res.data.page_info
		})
		.catch(err => {
			if (axios.isCancel(err)) return
			error.value = getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later."
		})
		.finally(() => {
			if (controller === current) loading.value = false
		})
}

function reload() {
	fetchPage(false)
}

function loadMore() {
	fetchPage(true)
}

function clearSearch() {
	search.value = ""
	reload()
}

function openDetail(indicator: OpenCTIIndicator) {
	selectedId.value = indicator.id
	showDetail.value = true
}

function rowProps(row: OpenCTIIndicator) {
	return { class: "cursor-pointer", onClick: () => openDetail(row) }
}

function isExpired(date: string | null): boolean {
	return !!date && dayjs(date).isBefore(dayjs())
}

const columns: DataTableColumns<OpenCTIIndicator> = [
	{
		title: "Indicator",
		key: "name",
		minWidth: 320,
		ellipsis: { tooltip: true },
		render: row => <span class="font-mono text-sm">{row.name || row.pattern || row.id}</span>
	},
	{
		title: "Type",
		key: "main_observable_type",
		width: 130,
		render: row => <span class="text-secondary font-mono text-xs">{row.main_observable_type || "—"}</span>
	},
	{
		title: "Score",
		key: "score",
		width: 80,
		render: row =>
			row.score === null ? (
				<span class="text-tertiary">—</span>
			) : (
				<NTag size="small" type={scoreTagType(row.score)} bordered={false} class="font-mono font-bold">
					{row.score}
				</NTag>
			)
	},
	{
		title: "Labels",
		key: "labels",
		width: 240,
		render: row => (
			<div class="flex flex-wrap gap-1">
				{row.labels.slice(0, 3).map(label => (
					<NTag size="small" round key={label.value}>
						{label.value}
					</NTag>
				))}
				{row.labels.length > 3 ? (
					<span class="text-secondary text-xs">{`+${row.labels.length - 3}`}</span>
				) : null}
			</div>
		)
	},
	{
		title: "Author",
		key: "created_by",
		width: 140,
		ellipsis: { tooltip: true },
		render: row => <span class="text-secondary text-sm">{row.created_by || "—"}</span>
	},
	{
		title: "Created",
		key: "created_at",
		width: 110,
		render: row => (
			<span class="text-secondary text-xs">
				{row.created_at ? formatDate(row.created_at, dFormats.date) : "—"}
			</span>
		)
	},
	{
		title: "Valid until",
		key: "valid_until",
		width: 130,
		render: row =>
			row.revoked ? (
				<NTag size="small" type="error" bordered={false}>
					revoked
				</NTag>
			) : row.valid_until ? (
				<span class={isExpired(row.valid_until) ? "text-error text-xs" : "text-secondary text-xs"}>
					{isExpired(row.valid_until) ? "expired " : ""}
					{formatDate(row.valid_until, dFormats.date)}
				</span>
			) : (
				<span class="text-tertiary">—</span>
			)
	}
]

// The select and the score box apply as soon as they change; free text waits
// for Enter, since OpenCTI's search matches whole tokens and a half-typed one
// would briefly empty the table.
watch([observableType, minScore], reload)

onBeforeMount(reload)
</script>
