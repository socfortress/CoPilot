<template>
	<div class="flex flex-col gap-3">
		<div class="flex flex-wrap items-end justify-between gap-3">
			<n-radio-group v-model:value="status" size="small">
				<n-radio-button value="open">Open</n-radio-button>
				<n-radio-button value="closed">Closed</n-radio-button>
				<n-radio-button value="all">All</n-radio-button>
			</n-radio-group>
			<p class="text-secondary max-w-xl text-xs">
				UBA alerts open when an entity's accumulated risk passes 100 (or one finding is strong enough on its
				own). Each is also an incident alert in CoPilot; a verdict here or there closes the loop in UBA.
			</p>
		</div>

		<UbaError v-if="error" :error />

		<n-data-table
			v-else
			:columns
			:data="alerts"
			:loading
			:row-key="(row: UbaAlert) => row.id"
			:row-props
			size="small"
			:scroll-x="900"
		/>

		<div v-if="total > PAGE_SIZE" class="flex justify-end">
			<n-pagination v-model:page="page" :page-size="PAGE_SIZE" :item-count="total" />
		</div>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { UbaAlert } from "@/types/uba"
import { NDataTable, NPagination, NRadioButton, NRadioGroup, NTag } from "naive-ui"
import { onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import UbaError from "./UbaError.vue"
import { entityTypeLabel, riskLabel, riskTagType } from "./utils"

const { customerCode, refreshKey = 0 } = defineProps<{ customerCode: string; refreshKey?: number }>()
const emit = defineEmits<{ open: [alertId: string] }>()

const PAGE_SIZE = 25
const dFormats = useSettingsStore().dateFormat
const status = ref<"open" | "closed" | "all">("open")
const page = ref(1)
const total = ref(0)
const loading = ref(false)
const error = ref<ApiError | null>(null)
const alerts = ref<UbaAlert[]>([])

function load() {
	loading.value = true
	error.value = null
	Api.uba
		.getAlerts(customerCode, {
			status: status.value === "all" ? null : status.value,
			page: page.value,
			page_size: PAGE_SIZE
		})
		.then(res => {
			alerts.value = res.data.alerts
			total.value = res.data.total
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
}

function rowProps(row: UbaAlert) {
	return { class: "cursor-pointer", onClick: () => emit("open", row.id) }
}

const columns: DataTableColumns<UbaAlert> = [
	{ title: "Opened", key: "opened_at", width: 170, render: row => String(formatDate(row.opened_at, dFormats.datetime)) },
	{
		title: "Entity",
		key: "entity_name",
		minWidth: 240,
		render: row => (
			<div class="flex min-w-0 flex-col">
				<span class="truncate font-medium">{row.entity_name || row.entity_key}</span>
				<span class="text-tertiary text-xs">{entityTypeLabel(row.entity_type)}</span>
			</div>
		)
	},
	{
		title: "Risk",
		key: "risk",
		width: 80,
		render: row => (
			<NTag type={riskTagType(row.risk)} size="small" round bordered={false}>
				{riskLabel(row.risk)}
			</NTag>
		)
	},
	{ title: "Updates", key: "update_count", width: 80 },
	{
		title: "Incident",
		key: "copilot_alert_id",
		width: 90,
		render: row => (row.copilot_alert_id ? `#${row.copilot_alert_id}` : "—")
	},
	{
		title: "Verdict",
		key: "verdict",
		width: 140,
		render: row =>
			row.verdict ? (
				<NTag type={row.verdict === "FALSE_POSITIVE" ? "default" : "error"} size="small" bordered={false}>
					{row.verdict === "FALSE_POSITIVE" ? "false positive" : "true positive"}
				</NTag>
			) : (
				<span class="text-tertiary text-xs">not triaged</span>
			)
	}
]

watch(page, load)
watch(status, () => {
	if (page.value === 1) load()
	else page.value = 1
})
watch(
	() => refreshKey,
	() => load()
)
onBeforeMount(load)
</script>
