<template>
	<div class="flex flex-col gap-3" data-testid="uba-alerts">
		<UbaToolbar>
			<SegmentedToggle v-model="status" :options="STATUS_OPTIONS" label="Alerts" test-id="uba-alert-status" />
			<template #summary>{{ summary }}</template>
			<template #hint>
				UBA alerts open when an entity's accumulated risk passes 100 (or one finding is strong enough on its
				own). Each is also an incident alert in CoPilot; a verdict here or there closes the loop in UBA.
			</template>
		</UbaToolbar>

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
			class="uba-table"
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
import { NButton, NDataTable, NPagination, NTag } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import SegmentedToggle from "@/components/common/SegmentedToggle.vue"
import { useNavigation } from "@/composables/useNavigation"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import UbaError from "./UbaError.vue"
import RiskMeter from "./ui/RiskMeter.vue"
import UbaToolbar from "./ui/UbaToolbar.vue"
import { entityTypeIcon, entityTypeLabel } from "./utils"

const { customerCode, refreshKey = 0 } = defineProps<{ customerCode: string; refreshKey?: number }>()
const emit = defineEmits<{ open: [alertId: string] }>()

const { routeIncidentManagementAlerts } = useNavigation()

const PAGE_SIZE = 25
const dFormats = useSettingsStore().dateFormat
const STATUS_OPTIONS: { value: "open" | "closed" | "all"; label: string }[] = [
	{ value: "open", label: "Open" },
	{ value: "closed", label: "Closed" },
	{ value: "all", label: "All" }
]
const status = ref<"open" | "closed" | "all">("open")
const page = ref(1)
const total = ref(0)
/** "1 open alert", "3 closed alerts", "4 alerts". */
const summary = computed(() => {
	const kind = status.value === "all" ? "" : `${status.value} `
	return `${total.value} ${kind}alert${total.value === 1 ? "" : "s"}`
})
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
	{
		title: "Opened",
		key: "opened_at",
		width: 170,
		render: row => (
			<span class="font-mono text-xs tabular-nums">{String(formatDate(row.opened_at, dFormats.datetime))}</span>
		)
	},
	{
		title: "Entity",
		key: "entity_name",
		minWidth: 260,
		render: row => (
			<div class="flex min-w-0 items-center gap-2.5">
				<span class="entity-icon" title={entityTypeLabel(row.entity_type)}>
					<Icon name={entityTypeIcon(row.entity_type)} size={14} />
				</span>
				<div class="flex min-w-0 flex-col">
					<span class="truncate font-medium">{row.entity_name || row.entity_key}</span>
					<span class="text-secondary text-[11px]">{entityTypeLabel(row.entity_type)}</span>
				</div>
			</div>
		)
	},
	{ title: "Risk", key: "risk", width: 120, render: row => <RiskMeter risk={row.risk} /> },
	{
		title: "Updates",
		key: "update_count",
		width: 80,
		align: "right",
		render: row => <span class="font-mono tabular-nums">{row.update_count}</span>
	},
	{
		title: "Incident",
		key: "copilot_alert_id",
		width: 100,
		render: row =>
			row.copilot_alert_id ? (
				<NButton
					text
					type="primary"
					class="font-mono"
					onClick={(e: MouseEvent) => {
						e.stopPropagation() // the row click opens the UBA alert drawer
						routeIncidentManagementAlerts(row.copilot_alert_id ?? undefined).navigate()
					}}
				>
					{`#${row.copilot_alert_id}`}
				</NButton>
			) : (
				<span class="text-tertiary">—</span>
			)
	},
	{
		title: "Verdict",
		key: "verdict",
		width: 140,
		render: row =>
			row.verdict ? (
				<NTag type={row.verdict === "FALSE_POSITIVE" ? "default" : "error"} size="small" round bordered={false}>
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
