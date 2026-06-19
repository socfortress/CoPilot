<template>
	<div class="flex flex-col">
		<div class="flex flex-col" :class="{ 'mb-30': selectedRules.length }">
			<GridViewToolbar
				v-model:search-query="searchQuery"
				v-model:show-filters="showFilters"
				v-model:selected-platform="selectedPlatform"
				v-model:selected-severity="selectedSeverity"
				v-model:selected-status="selectedStatus"
				v-model:has-graylog-filter="hasGraylogFilter"
				hide-selection-switch
				:pagination
				:select-mode
				:refreshing
				@refresh="handleRefresh"
				@toggle-select-mode="toggleSelectMode"
				@reset-filters="resetFilters"
			>
				<n-pagination
					v-model:page="pagination.current"
					:page-size="pagination.size"
					:item-count="pagination.filtered"
					:page-slot="5"
				/>
			</GridViewToolbar>

			<n-spin :show="loading">
				<div class="my-3">
					<div
						v-if="list.length"
						class="grid grid-cols-1 gap-4 @2xl:grid-cols-2 @4xl:grid-cols-3 @6xl:grid-cols-4"
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
		</div>
		<GridViewSelectionBar
			:select-mode
			:selected-rules
			@clear="clearSelection"
			@provision-success="onBulkProvisionSuccess"
		/>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type {
	BulkProvisionGraylogAlertResponse,
	PlatformFilter,
	RuleListQuery,
	RuleSeverity,
	RuleStatus,
	RuleSummary
} from "@/types/copilotSearches"
import { watchDebounced } from "@vueuse/core"
import axios from "axios"
import { NEmpty, NPagination, NSpin, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
import RuleCard from "../RuleCard.vue"
import GridViewSelectionBar from "./GridViewSelectionBar.vue"
import GridViewToolbar from "./GridViewToolbar.vue"

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
				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
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
	} catch (err) {
		const error = err as { response?: { data?: { message?: string } } }
		message.error(getApiErrorMessage(error as ApiError) || "Failed to refresh cache")
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

const selectMode = ref(true)
const selection = ref<Set<string>>(new Set())
const selectionCache = ref<Map<string, RuleSummary>>(new Map())

const selectedRules = computed(() => Array.from(selectionCache.value.values()))

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

function onBulkProvisionSuccess(res: BulkProvisionGraylogAlertResponse) {
	const next = { ...provisionedMap.value }
	for (const r of res.results) {
		if (r.status === "provisioned" || r.status === "skipped") {
			next[r.rule_id] = true
		}
	}
	provisionedMap.value = next
}
</script>
