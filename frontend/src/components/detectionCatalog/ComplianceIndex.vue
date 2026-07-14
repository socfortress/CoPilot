<template>
	<div class="@container flex flex-col gap-4">
		<div class="flex flex-col gap-1">
			<h3 class="text-lg font-semibold">Compliance Coverage</h3>
			<p class="text-secondary text-sm">
				Wazuh rules grouped by control ID for the selected compliance framework. Each row shows how many rules
				cover that control and how active they've been — useful for auditor questions like "what coverage do we
				have for PCI DSS 10.2.4?".
			</p>
		</div>

		<!-- HERO STATS for the selected framework -->
		<div v-if="!loading && pivot" class="grid grid-cols-1 gap-4 @2xl:grid-cols-3">
			<CardLink
				v-for="tile in complianceStatTiles"
				:key="tile.id"
				:title="tile.label"
				:value="tile.value"
				:icon-left="tile.icon"
				:color="tile.color"
				:subtitle="tile.sub"
				size="small"
			/>
		</div>

		<!-- Framework selector + control search -->
		<div class="flex flex-wrap items-center gap-2">
			<n-select
				v-model:value="selectedFramework"
				:options="frameworkOptions"
				:loading="loadingFrameworks"
				size="small"
				class="min-w-80 flex-1"
				@update:value="load"
			/>
			<n-input
				v-model:value="filter"
				size="small"
				placeholder="Filter by control ID…"
				clearable
				class="min-w-80 flex-1"
			>
				<template #prefix><Icon name="carbon:search" /></template>
			</n-input>
			<Badge v-if="pivot" type="splitted" color="primary" class="shrink-0">
				<template #label>Showing</template>
				<template #value>{{ filteredGroups.length }} / {{ pivot.groups.length }}</template>
			</Badge>
		</div>

		<n-data-table
			:columns
			:data="filteredGroups"
			:loading
			size="small"
			:pagination
			:scroll-x="1110"
			class="catalog-table"
		/>

		<!-- Control drill-down modal -->
		<n-modal
			v-model:show="showGroupModal"
			preset="card"
			:style="{ maxWidth: 'min(720px, 92vw)' }"
			:title="modalTitle"
			:bordered="false"
			segmented
		>
			<ComplianceDetail v-if="modalGroup" :group="modalGroup" />
		</n-modal>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns, SelectOption } from "naive-ui"
import type { ApiError } from "@/types/common"
import type {
	CatalogComplianceFramework,
	CatalogComplianceGroupRow,
	CatalogComplianceResponse
} from "@/types/detection-catalog"
import { NDataTable, NInput, NModal, NSelect, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardLink from "@/components/common/cards/CardLink.vue"
import Dot, { hitsToDotVariant } from "@/components/common/Dot.vue"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import { getApiErrorMessage } from "@/utils"
import ComplianceDetail from "./ComplianceDetail.vue"

interface ComplianceStatTile {
	id: string
	label: string
	value: string
	icon: string
	sub: string
	color?: "warning" | "success" | "danger" | "primary"
}

const message = useMessage()
const { routeDetectionCatalogComplianceGroup } = useNavigation()

const frameworks = ref<CatalogComplianceFramework[]>([])
const selectedFramework = ref<string>("pci_dss")
const pivot = ref<CatalogComplianceResponse | null>(null)
const loadingFrameworks = ref(false)
const loading = ref(false)
const filter = ref("")

const modalGroup = ref<CatalogComplianceGroupRow | null>(null)
// The modal is open exactly when a control group is selected — closing it clears the selection.
const showGroupModal = computed({
	get: () => modalGroup.value !== null,
	set: (open: boolean) => {
		if (!open) modalGroup.value = null
	}
})
const modalTitle = computed(() =>
	modalGroup.value ? `${pivot.value?.framework_label ?? ""} ${modalGroup.value.control}` : "Compliance Control"
)

const ControlIcon = "carbon:certificate-check"
const RulesIcon = "carbon:document-security"
const UntaggedIcon = "carbon:document-blank"

const pagination = {
	pageSize: 25,
	pageSizes: [10, 25, 50, 100],
	showSizePicker: true
}

const frameworkOptions = computed<SelectOption[]>(() => frameworks.value.map(f => ({ label: f.label, value: f.key })))

const filteredGroups = computed<CatalogComplianceGroupRow[]>(() => {
	const groups = pivot.value?.groups || []
	const q = filter.value.trim().toLowerCase()
	if (!q) return groups
	return groups.filter(g => g.control.toLowerCase().includes(q))
})

const complianceStatTiles = computed<ComplianceStatTile[]>(() => {
	if (!pivot.value) return []

	return [
		{
			id: "controls",
			label: `${pivot.value.framework_label} controls`,
			value: pivot.value.control_count.toLocaleString(),
			icon: ControlIcon,
			sub: "Distinct control IDs",
			color: "primary"
		},
		{
			id: "rules-tagged",
			label: "Rules tagged",
			value: pivot.value.rules_with_compliance.toLocaleString(),
			icon: RulesIcon,
			sub: `of ${pivot.value.total_rules.toLocaleString()} total Wazuh rules`
		},
		{
			id: "rules-without-tag",
			label: "Rules without tag",
			value: (pivot.value.total_rules - pivot.value.rules_with_compliance).toLocaleString(),
			icon: UntaggedIcon,
			sub: "Not classified for this framework",
			color: "warning"
		}
	]
})

function openGroup(group: CatalogComplianceGroupRow) {
	modalGroup.value = group
}

const columns: DataTableColumns<CatalogComplianceGroupRow> = [
	{
		title: "Activity",
		key: "total_hits_30d",
		width: 150,
		fixed: "left",
		defaultSortOrder: "descend",
		sorter: (a, b) => a.total_hits_30d - b.total_hits_30d,
		render: row => {
			if (row.total_hits_30d === 0) {
				return (
					<div class="flex items-center gap-1.5">
						<Dot variant="muted" />
						<span class="text-secondary text-xs">No hits 30d</span>
					</div>
				)
			}
			return (
				<div class="flex items-center gap-2">
					<Dot variant={hitsToDotVariant(row.total_hits_30d)} />
					<div class="flex flex-col leading-tight">
						<span class="font-mono text-xs font-medium">{row.total_hits_30d.toLocaleString()}</span>
						<span class="text-secondary text-xs">{`${row.total_hits_7d.toLocaleString()} in 7d`}</span>
					</div>
				</div>
			)
		}
	},
	{
		title: "Control",
		key: "control",
		width: 200,
		sorter: (a, b) => a.control.localeCompare(b.control),
		render: row => <span class="font-mono text-sm font-medium">{row.control}</span>
	},
	{
		title: "Rules",
		key: "rule_count",
		width: 100,
		sorter: (a, b) => a.rule_count - b.rule_count,
		render: row => (
			<NTag size="small" type="primary">
				{row.rule_count}
			</NTag>
		)
	},
	{
		title: "Rule IDs (preview)",
		key: "rule_ids",
		render: row => (
			<div class="flex flex-wrap gap-1">
				{row.rule_ids.slice(0, 10).map(rid => (
					<NTag key={rid} size="small">
						{rid}
					</NTag>
				))}
				{row.rule_ids.length > 10 && (
					<NTag size="small" type="default" bordered={false}>{`+${row.rule_ids.length - 10}`}</NTag>
				)}
			</div>
		)
	},
	{
		title: "",
		key: "actions",
		width: 110,
		fixed: "right",
		render: row => (
			<div onClick={e => e.stopPropagation()}>
				<EntityDetailsButton
					size="tiny"
					route={routeDetectionCatalogComplianceGroup(selectedFramework.value, row.control)}
					onView={() => openGroup(row)}
				/>
			</div>
		)
	}
]

function loadFrameworks() {
	loadingFrameworks.value = true
	Api.detectionCatalog
		.listComplianceFrameworks()
		.then(res => {
			if (res.data?.success) {
				frameworks.value = res.data.frameworks || []
				if (frameworks.value.length && !frameworks.value.some(f => f.key === selectedFramework.value)) {
					selectedFramework.value = frameworks.value[0].key
				}
			}
		})
		.catch(() => {
			/* Non-fatal — analyst can retry. */
		})
		.finally(() => {
			loadingFrameworks.value = false
			load()
		})
}

function load() {
	if (!selectedFramework.value) return
	loading.value = true
	Api.detectionCatalog
		.getCompliancePivot(selectedFramework.value)
		.then(res => {
			if (res.data?.success) pivot.value = res.data
			else message.warning(res.data?.message || "Failed to load compliance pivot")
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Failed to load compliance pivot")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(loadFrameworks)
</script>
