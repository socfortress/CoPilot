<template>
	<div class="flex flex-col">
		<div class="flex flex-wrap items-center justify-end gap-2">
			<div class="flex min-w-80 grow gap-2">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-default rounded-lg">
							<n-button size="small" class="cursor-help!">
								<template #icon>
									<Icon :name="InfoIcon" />
								</template>
							</n-button>
						</div>
					</template>
					<div class="flex flex-col gap-2">
						<div class="box">
							Total Rules:
							<code>{{ pagination.total }}</code>
						</div>
						<div class="box">
							Filtered:
							<code>{{ pagination.filtered }}</code>
						</div>
					</div>
				</n-popover>

				<n-input
					v-model:value="searchQuery"
					size="small"
					placeholder="Search rules..."
					class="max-w-120"
					clearable
				>
					<template #prefix>
						<Icon :name="SearchIcon" />
					</template>
				</n-input>

				<n-popover :show="showFilters" trigger="manual" overlap placement="right" class="px-0!">
					<template #trigger>
						<div class="bg-default rounded-lg">
							<n-badge :show="filtered" dot type="success" :offset="[-4, 0]">
								<n-button size="small" @click="showFilters = true">
									<template #icon>
										<Icon :name="FilterIcon" />
									</template>
								</n-button>
							</n-badge>
						</div>
					</template>
					<div class="divide-border flex w-50 flex-col gap-0 divide-y">
						<div class="flex flex-col gap-2.5 px-3 pt-1 pb-3">
							<n-select
								v-model:value="selectedPlatform"
								:options="platformOptions"
								size="small"
								placeholder="Platform"
								class="w-full"
								clearable
								:consistent-menu-width="false"
							/>

							<n-select
								v-model:value="selectedSeverity"
								:options="severityOptions"
								clearable
								size="small"
								placeholder="Severity"
								class="w-full"
								:consistent-menu-width="false"
							/>

							<n-select
								v-model:value="selectedStatus"
								:options="statusOptions"
								clearable
								size="small"
								placeholder="Status"
								class="w-full"
								:consistent-menu-width="false"
							/>

							<n-checkbox v-model:checked="hasGraylogFilter" size="small">
								<span class="text-xs">Graylog Only</span>
							</n-checkbox>
						</div>
						<div class="flex justify-between gap-2 px-3 pt-2">
							<div class="flex justify-start gap-2">
								<n-button size="small" quaternary @click="showFilters = false">Close</n-button>
							</div>
							<div class="flex justify-end gap-2">
								<n-button size="small" secondary @click="resetFilters()">Reset</n-button>
							</div>
						</div>
					</div>
				</n-popover>
			</div>

			<n-button size="small" :type="selectMode ? 'primary' : 'default'" @click="toggleSelectMode">
				<template #icon>
					<Icon :name="SelectIcon" />
				</template>
				{{ selectMode ? "Exit select" : "Select" }}
			</n-button>

			<n-button size="small" :loading="refreshing" @click="handleRefresh">
				<template #icon>
					<Icon :name="RefreshIcon" />
				</template>
				Refresh Cache
			</n-button>

			<n-pagination
				v-model:page="pagination.current"
				:page-size="pagination.size"
				:item-count="pagination.filtered"
				:page-slot="5"
			/>
		</div>

		<n-spin :show="loading">
			<div class="my-3">
				<div
					v-if="list.length"
					class="grid grid-cols-1 gap-4 @2xl:grid-cols-2 @5xl:grid-cols-3 @6xl:grid-cols-4"
				>
					<RuleCard
						v-for="rule of list"
						:key="rule.id"
						:rule
						:provisioned="provisionedMap[rule.id] === true"
						:selectable="selectMode"
						:selected="selection.has(rule.id)"
						@update:selected="v => toggleRuleSelected(rule.id, v)"
					/>
				</div>

				<n-empty v-else-if="!loading" description="No rules found" class="h-48 justify-center" />
			</div>
		</n-spin>

		<div class="flex justify-end">
			<n-pagination
				v-if="list.length > 3"
				v-model:page="pagination.current"
				:page-size="pagination.size"
				:item-count="pagination.filtered"
				:page-slot="6"
			/>
		</div>

		<Transition name="fade-up">
			<div v-if="selectMode && selection.size > 0" class="selection-footer">
				<div class="text-default text-sm">
					<strong>{{ selection.size }}</strong>
					selected
					<span class="text-tertiary ml-2 text-xs">({{ provisionableSelectedCount }} with Graylog query)</span>
				</div>

				<div class="ml-auto flex items-center gap-2">
					<n-tooltip placement="top">
						<template #trigger>
							<n-button
								size="small"
								type="primary"
								:disabled="provisionableSelectedCount === 0"
								@click="openBulkProvisionModal"
							>
								<template #icon>
									<Icon :name="ProvisionIcon" />
								</template>
								Provision selected
							</n-button>
						</template>
						<template v-if="provisionableSelectedCount === 0">
							None of the selected rules has a Graylog query.
						</template>
						<template v-else>
							Provision {{ provisionableSelectedCount }} rule{{
								provisionableSelectedCount === 1 ? "" : "s"
							}}
							as Graylog event definitions.
						</template>
					</n-tooltip>

					<n-button size="small" @click="exportSelectedCsv">
						<template #icon>
							<Icon :name="ExportIcon" />
						</template>
						CSV
					</n-button>
					<n-button size="small" @click="exportSelectedJson">
						<template #icon>
							<Icon :name="ExportIcon" />
						</template>
						JSON
					</n-button>

					<n-button size="small" quaternary @click="clearSelection">Clear</n-button>
				</div>
			</div>
		</Transition>

		<BulkProvisionModal
			v-model:show="showBulkProvisionModal"
			:rule-ids="selectedRuleIdsWithGraylog"
			:provisionable-count="provisionableSelectedCount"
			@success="onBulkProvisionSuccess"
		/>
	</div>
</template>

<script setup lang="ts">
import type {
	BulkProvisionGraylogAlertResponse,
	PlatformFilter,
	RuleListQuery,
	RuleSeverity,
	RuleStatus,
	RuleSummary
} from "@/types/copilotSearches.d"
import { watchDebounced } from "@vueuse/core"
import axios from "axios"
import {
	NBadge,
	NButton,
	NCheckbox,
	NEmpty,
	NInput,
	NPagination,
	NPopover,
	NSelect,
	NSpin,
	NTooltip,
	useMessage
} from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import BulkProvisionModal from "./BulkProvisionModal.vue"
import RuleCard from "./RuleCard.vue"

const loading = ref(false)
const refreshing = ref(false)
const message = useMessage()
const list = ref<RuleSummary[]>([])
const provisionedMap = ref<Record<string, boolean>>({})
const pagination = ref({
	current: 1,
	size: 24,
	total: 0,
	filtered: 0
})

const selectedPlatform = ref<PlatformFilter | null>(null)
const selectedSeverity = ref<RuleSeverity | null>(null)
const selectedStatus = ref<RuleStatus | null>(null)
const searchQuery = ref<string | null>(null)
const hasGraylogFilter = ref(false)
const showFilters = ref(false)

const filtered = computed<boolean>(() => {
	return !!selectedPlatform.value || !!selectedSeverity.value || !!selectedStatus.value || !!hasGraylogFilter.value
})

const InfoIcon = "carbon:information"
const FilterIcon = "carbon:filter-edit"
const SearchIcon = "carbon:search"
const RefreshIcon = "carbon:renew"
const SelectIcon = "carbon:checkbox-checked"
const ProvisionIcon = "carbon:add-alt"
const ExportIcon = "carbon:download"

const platformOptions = [
	{ label: "Linux", value: "linux" },
	{ label: "Windows", value: "windows" },
	{ label: "PowerShell", value: "powershell" },
	{ label: "CVE", value: "cve" }
]

const severityOptions = [
	{ label: "Low", value: "low" },
	{ label: "Medium", value: "medium" },
	{ label: "High", value: "high" },
	{ label: "Critical", value: "critical" }
]

const statusOptions = [
	{ label: "Production", value: "production" },
	{ label: "Experimental", value: "experimental" },
	{ label: "Deprecated", value: "deprecated" }
]

let abortController: AbortController | null = null

function resetFilters() {
	selectedPlatform.value = null
	selectedSeverity.value = null
	selectedStatus.value = null
	hasGraylogFilter.value = false
	showFilters.value = false
}

async function refreshProvisionedMap() {
	const ids = list.value.map(r => r.id)
	provisionedMap.value = {}
	if (!ids.length) return
	try {
		const res = await Api.copilotSearches.checkGraylogProvisioningStatus(ids)
		if (res.data?.success && !res.data.warning) {
			provisionedMap.value = res.data.provisioned || {}
		}
	} catch {
		// Silent — if Graylog is unreachable, just don't show the chip.
	}
}

function getList() {
	abortController?.abort()
	abortController = new AbortController()

	loading.value = true

	const query: RuleListQuery = {
		skip: (pagination.value.current - 1) * pagination.value.size,
		limit: pagination.value.size,
		platform: selectedPlatform.value || undefined,
		severity: selectedSeverity.value || undefined,
		status: selectedStatus.value || undefined,
		search: searchQuery.value || undefined,
		has_graylog: hasGraylogFilter.value ? true : undefined
	}

	Api.copilotSearches
		.getRules(query, abortController.signal)
		.then(res => {
			loading.value = false

			if (res.data.success) {
				list.value = res.data?.rules || []
				pagination.value.total = res.data?.total || 0
				pagination.value.filtered = res.data?.filtered || 0
				refreshProvisionedMap()
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
				loading.value = false
			}
		})
}

async function handleRefresh() {
	refreshing.value = true
	try {
		const res = await Api.copilotSearches.refreshCache()
		if (res.data.success) {
			message.success(`Cache refreshed! Loaded ${res.data.rules_loaded} rules.`)
			getList()
		} else {
			message.warning(res.data?.message || "Failed to refresh cache")
		}
	} catch (err: unknown) {
		const error = err as { response?: { data?: { message?: string } } }
		message.error(error.response?.data?.message || "Failed to refresh cache")
	} finally {
		refreshing.value = false
	}
}

watchDebounced(
	[selectedPlatform, selectedSeverity, selectedStatus, searchQuery, hasGraylogFilter, () => pagination.value.current],
	getList,
	{
		deep: true,
		debounce: 300,
		immediate: true
	}
)

const selectMode = ref(false)
const selection = ref<Set<string>>(new Set())
const selectionCache = ref<Map<string, RuleSummary>>(new Map())
const showBulkProvisionModal = ref(false)

const provisionableSelectedCount = computed(
	() => Array.from(selectionCache.value.values()).filter(r => r.has_graylog_query).length
)

const selectedRuleIdsWithGraylog = computed(() =>
	Array.from(selectionCache.value.values())
		.filter(r => r.has_graylog_query)
		.map(r => r.id)
)

function toggleSelectMode() {
	selectMode.value = !selectMode.value
	if (!selectMode.value) clearSelection()
}

function toggleRuleSelected(ruleId: string, value: boolean) {
	if (value) {
		selection.value.add(ruleId)
		const summary = list.value.find(r => r.id === ruleId)
		if (summary) selectionCache.value.set(ruleId, summary)
	} else {
		selection.value.delete(ruleId)
		selectionCache.value.delete(ruleId)
	}
	selection.value = new Set(selection.value)
	selectionCache.value = new Map(selectionCache.value)
}

function clearSelection() {
	selection.value = new Set()
	selectionCache.value = new Map()
}

function openBulkProvisionModal() {
	if (provisionableSelectedCount.value === 0) return
	showBulkProvisionModal.value = true
}

function onBulkProvisionSuccess(res: BulkProvisionGraylogAlertResponse) {
	const next = { ...provisionedMap.value }
	for (const r of res.results) {
		if (r.status === "provisioned" || r.status === "skipped") {
			next[r.rule_id] = true
		}
	}
	provisionedMap.value = next
}

function downloadBlob(blob: Blob, filename: string) {
	const url = URL.createObjectURL(blob)
	const link = document.createElement("a")
	link.href = url
	link.download = filename
	document.body.appendChild(link)
	link.click()
	document.body.removeChild(link)
	URL.revokeObjectURL(url)
}

function exportSelectedCsv() {
	const rules = Array.from(selectionCache.value.values())
	if (!rules.length) return
	const header = [
		"id",
		"name",
		"severity",
		"platform",
		"status",
		"has_graylog_query",
		"mitre_attack_id",
		"description"
	]
	const rows = rules.map(r => [
		r.id,
		r.name,
		r.severity,
		r.platform,
		r.status,
		String(r.has_graylog_query),
		(r.mitre_attack_id || []).join("|"),
		(r.description || "").replace(/\s+/g, " ")
	])
	const csv = [header, ...rows]
		.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(","))
		.join("\n")
	const stamp = new Date().toISOString().slice(0, 10)
	downloadBlob(new Blob([csv], { type: "text/csv;charset=utf-8;" }), `copilot-searches-selected-${stamp}.csv`)
}

function exportSelectedJson() {
	const rules = Array.from(selectionCache.value.values())
	if (!rules.length) return
	const json = JSON.stringify(rules, null, 2)
	const stamp = new Date().toISOString().slice(0, 10)
	downloadBlob(
		new Blob([json], { type: "application/json;charset=utf-8;" }),
		`copilot-searches-selected-${stamp}.json`
	)
}
</script>

<style scoped lang="scss">
.selection-footer {
	position: fixed;
	bottom: 16px;
	left: 50%;
	transform: translateX(-50%);
	z-index: 50;
	display: flex;
	align-items: center;
	gap: 16px;
	min-width: min(680px, 92vw);
	max-width: 92vw;
	padding: 10px 16px;
	background: var(--bg-secondary-color);
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius);
	box-shadow: 0 6px 24px rgba(0, 0, 0, 0.25);
}

.fade-up-enter-active,
.fade-up-leave-active {
	transition:
		opacity 0.2s ease,
		transform 0.2s ease;
}
.fade-up-enter-from,
.fade-up-leave-to {
	opacity: 0;
	transform: translate(-50%, 12px);
}
</style>
