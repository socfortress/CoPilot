<template>
	<div class="flex flex-col gap-3" data-testid="uba-entities">
		<UbaToolbar>
			<n-input
				v-model:value="search"
				placeholder="Search name or key"
				clearable
				size="small"
				class="w-64!"
				@keyup.enter="reload()"
				@clear="reload()"
			>
				<template #prefix><Icon name="carbon:search" :size="14" /></template>
			</n-input>
			<n-select v-model:value="entityType" :options="typeOptions" clearable placeholder="Any type" size="small" class="w-44!" />
			<label class="flex items-center gap-2 pl-1 text-xs">
				<n-switch v-model:value="ownOnly" size="small" />
				<span>UBA findings only</span>
				<n-tooltip style="max-width: 300px">
					<template #trigger><Icon name="carbon:information" :size="13" class="text-tertiary" /></template>
					Rank by UBA's own findings, leaving out risk from native alerts (Wazuh rules). Hosts with months of
					noisy native alerts otherwise fill the top of the list.
				</n-tooltip>
			</label>
			<template #summary>{{ total }} {{ total === 1 ? "entity" : "entities" }} · highest risk first</template>
		</UbaToolbar>

		<UbaError v-if="error" :error />

		<n-data-table
			v-else
			:columns
			:data="entities"
			:loading
			:row-key="(row: UbaEntitySummary) => row.entity_key"
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
import type { DataTableColumns, SelectOption } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { UbaEntitySummary } from "@/types/uba"
import { NDataTable, NInput, NPagination, NSelect, NSwitch, NTag, NTooltip } from "naive-ui"
import { onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import UbaError from "./UbaError.vue"
import RiskMeter from "./ui/RiskMeter.vue"
import UbaToolbar from "./ui/UbaToolbar.vue"
import { entityTypeIcon, entityTypeLabel } from "./utils"

const { customerCode } = defineProps<{ customerCode: string }>()
const emit = defineEmits<{ open: [entityKey: string] }>()

const PAGE_SIZE = 25
const typeOptions: SelectOption[] = [
	{ label: "User (actor)", value: "actor" },
	{ label: "User (target)", value: "target" },
	{ label: "Host", value: "host" },
	{ label: "Address", value: "src_ip" }
]
const dFormats = useSettingsStore().dateFormat

const search = ref("")
const entityType = ref<string | null>(null)
const ownOnly = ref(false)
const page = ref(1)
const total = ref(0)
const loading = ref(false)
const error = ref<ApiError | null>(null)
const entities = ref<UbaEntitySummary[]>([])
let controller: AbortController | null = null

function load() {
	controller?.abort()
	controller = new AbortController()
	loading.value = true
	error.value = null
	Api.uba
		.getEntities(
			customerCode,
			{
				q: search.value || undefined,
				entity_type: entityType.value || undefined,
				native: !ownOnly.value,
				page: page.value,
				page_size: PAGE_SIZE
			},
			controller.signal
		)
		.then(res => {
			entities.value = res.data.entities
			total.value = res.data.total
		})
		.catch((err: ApiError) => {
			if (err.code !== "ERR_CANCELED") error.value = err
		})
		.finally(() => {
			loading.value = false
		})
}

function reload() {
	if (page.value === 1) load()
	else page.value = 1
}

function rowProps(row: UbaEntitySummary) {
	return { class: "cursor-pointer", onClick: () => emit("open", row.entity_key) }
}

const columns: DataTableColumns<UbaEntitySummary> = [
	{
		title: "Risk",
		key: "risk",
		width: 120,
		render: row => <RiskMeter risk={row.risk} />
	},
	{
		title: "Entity",
		key: "entity_name",
		minWidth: 280,
		render: row => (
			<div class="flex min-w-0 items-center gap-2.5">
				<span class="entity-icon" title={entityTypeLabel(row.entity_type)}>
					<Icon name={entityTypeIcon(row.entity_type)} size={14} />
				</span>
				<div class="flex min-w-0 flex-col">
					<span class="truncate font-medium">{row.entity_name || row.entity_key}</span>
					{row.entity_name ? <span class="text-tertiary truncate font-mono text-[11px]">{row.entity_key}</span> : null}
				</div>
			</div>
		)
	},
	{ title: "Type", key: "entity_type", width: 90, render: row => <span class="text-secondary text-xs">{entityTypeLabel(row.entity_type)}</span> },
	{ title: "Rules", key: "rules", width: 70, align: "right", render: row => <span class="font-mono tabular-nums">{row.rules}</span> },
	{
		title: "Findings 24 h",
		key: "signals_24h",
		width: 120,
		align: "right",
		render: row => <span class="font-mono tabular-nums">{row.signals_24h}</span>
	},
	{
		title: "Last finding",
		key: "last_signal",
		width: 170,
		render: row => (
			<span class="text-secondary font-mono text-xs tabular-nums">
				{row.last_signal ? String(formatDate(row.last_signal, dFormats.datetime)) : "—"}
			</span>
		)
	},
	{
		title: "Alert",
		key: "open_alert_id",
		width: 90,
		render: row =>
			row.open_alert_id ? (
				<NTag type="error" size="small" round bordered={false}>
					{{ icon: () => <Icon name="carbon:warning-alt-filled" size={12} />, default: () => "open" }}
				</NTag>
			) : null
	}
]

watch(page, load)
watch([entityType, ownOnly], reload)
onBeforeMount(load)
</script>
