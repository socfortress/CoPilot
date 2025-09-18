<template>
	<div class="flex flex-col gap-4">
		<n-alert type="info">
			SCA Overview provides real-time Security Configuration Assessment results from Wazuh Manager across all
			agents with comprehensive compliance scoring.
		</n-alert>

		<div ref="header" class="flex items-center justify-end gap-2">
			<n-pagination
				v-model:page="currentPage"
				v-model:page-size="pageSize"
				:page-slot
				:page-sizes
				:item-count="totalCount"
				:show-size-picker
			/>
			<n-badge :show="filtered" dot type="success" :offset="[-4, 0]">
				<n-button size="small" secondary @click="showFiltersView = !showFiltersView">
					<template #icon>
						<Icon :name="FilterIcon"></Icon>
					</template>
				</n-button>
			</n-badge>
		</div>

		<CollapseKeepAlive :show="showFiltersView" embedded arrow="top-right">
			<ListFilters class="p-3" @submit="applyFilters" @mounted="filtersCTX = $event" />
		</CollapseKeepAlive>

		<!-- Statistics Cards -->
		<div class="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
			<div class="stat-card">
				<div class="stat-header">
					<Icon :name="TotalIcon" :size="20" class="text-blue-600" />
					<span class="stat-title">Total</span>
				</div>
				<div class="stat-value">{{ totalCount.toLocaleString() }}</div>
			</div>

			<div class="stat-card excellent clickable" @click="selectComplianceLevel(ScaComplianceLevel.Excellent)">
				<div class="stat-header">
					<Icon :name="ExcellentIcon" :size="20" class="text-green-600" />
					<span class="stat-title">Excellent</span>
				</div>
				<div class="stat-value">{{ stats.excellent.toLocaleString() }}</div>
				<div class="stat-percentage">{{ getPercentage(stats.excellent) }}%</div>
			</div>

			<div class="stat-card good clickable" @click="selectComplianceLevel(ScaComplianceLevel.Good)">
				<div class="stat-header">
					<Icon :name="GoodIcon" :size="20" class="text-blue-600" />
					<span class="stat-title">Good</span>
				</div>
				<div class="stat-value">{{ stats.good.toLocaleString() }}</div>
				<div class="stat-percentage">{{ getPercentage(stats.good) }}%</div>
			</div>

			<div class="stat-card average clickable" @click="selectComplianceLevel(ScaComplianceLevel.Average)">
				<div class="stat-header">
					<Icon :name="AverageIcon" :size="20" class="text-yellow-600" />
					<span class="stat-title">Average</span>
				</div>
				<div class="stat-value">{{ stats.average.toLocaleString() }}</div>
				<div class="stat-percentage">{{ getPercentage(stats.average) }}%</div>
			</div>

			<div class="stat-card poor clickable" @click="selectComplianceLevel(ScaComplianceLevel.Poor)">
				<div class="stat-header">
					<Icon :name="PoorIcon" :size="20" class="text-orange-600" />
					<span class="stat-title">Poor</span>
				</div>
				<div class="stat-value">{{ stats.poor.toLocaleString() }}</div>
				<div class="stat-percentage">{{ getPercentage(stats.poor) }}%</div>
			</div>

			<div class="stat-card critical clickable" @click="selectComplianceLevel(ScaComplianceLevel.Critical)">
				<div class="stat-header">
					<Icon :name="CriticalIcon" :size="20" class="text-red-600" />
					<span class="stat-title">Critical</span>
				</div>
				<div class="stat-value">{{ stats.critical.toLocaleString() }}</div>
				<div class="stat-percentage">{{ getPercentage(stats.critical) }}%</div>
			</div>
		</div>

		<!-- Coverage Cards -->
		<div class="flex max-w-sm flex-col gap-3 p-2">
			<div class="mb-2 text-sm font-medium">SCA Overview</div>

			<div class="grid grid-cols-2 gap-3 text-xs">
				<div class="flex justify-between">
					<span>Total Policies:</span>
					<code class="font-mono">{{ totalCount.toLocaleString() }}</code>
				</div>
			</div>

			<div class="border-t pt-2">
				<div class="mb-2 text-xs font-medium">Compliance Distribution</div>
				<div class="grid grid-cols-2 gap-2 text-xs">
					<div class="flex justify-between">
						<span class="text-green-600">Excellent:</span>
						<span class="font-mono">
							{{ stats.excellent.toLocaleString() }} ({{ getPercentage(stats.excellent) }}%)
						</span>
					</div>
					<div class="flex justify-between">
						<span class="text-blue-600">Good:</span>
						<span class="font-mono">
							{{ stats.good.toLocaleString() }} ({{ getPercentage(stats.good) }}%)
						</span>
					</div>
					<div class="flex justify-between">
						<span class="text-yellow-600">Average:</span>
						<span class="font-mono">
							{{ stats.average.toLocaleString() }} ({{ getPercentage(stats.average) }}%)
						</span>
					</div>
					<div class="flex justify-between">
						<span class="text-orange-600">Poor:</span>
						<span class="font-mono">
							{{ stats.poor.toLocaleString() }} ({{ getPercentage(stats.poor) }}%)
						</span>
					</div>
					<div class="flex justify-between">
						<span class="text-red-600">Critical:</span>
						<span class="font-mono">
							{{ stats.critical.toLocaleString() }} ({{ getPercentage(stats.critical) }}%)
						</span>
					</div>
				</div>
			</div>

			<div class="border-t pt-2">
				<div class="mb-2 text-xs font-medium">Coverage</div>
				<div class="space-y-1 text-xs">
					<div class="flex justify-between">
						<span>Agents:</span>
						<span class="font-mono">
							{{ overviewData?.total_agents?.toLocaleString() || 0 }}
						</span>
					</div>
					<div class="flex justify-between">
						<span>Policies:</span>
						<span class="font-mono">
							{{ overviewData?.total_policies?.toLocaleString() || 0 }}
						</span>
					</div>
					<div class="flex justify-between">
						<span>Avg Score:</span>
						<span class="font-mono">{{ overviewData?.average_score?.toFixed(1) || 0 }}%</span>
					</div>
				</div>
			</div>
		</div>

		<!-- Top 5 Policies by Compliance Score -->
		<div v-if="topPoliciesByScore.length > 0" class="mb-4">
			<h3 class="mb-3 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
				<Icon :name="TopPoliciesIcon" :size="20" class="text-green-600" />
				Top 5 Policies by Compliance Score
			</h3>
			<div class="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
				<div
					v-for="(policy, index) in topPoliciesByScore.slice(0, 5)"
					:key="`${policy.policy_id}-${policy.score}`"
					class="policy-card clickable"
					:class="{
						'rank-1': index === 0,
						'rank-2': index === 1,
						'rank-3': index === 2
					}"
					@click="selectPolicyID(policy.policy_id)"
				>
					<div class="policy-header">
						<div class="policy-rank">
							<Icon
								:name="index < 3 ? 'carbon:trophy' : 'carbon:security'"
								:size="16"
								:class="
									index === 0
										? 'text-yellow-500'
										: index === 1
											? 'text-gray-400'
											: index === 2
												? 'text-amber-600'
												: 'text-green-500'
								"
							/>
							<span class="rank-number">#{{ index + 1 }}</span>
						</div>
						<Badge
							:color="getComplianceLevelColor(getComplianceLevel(policy.score))"
							type="splitted"
							size="small"
						>
							<template #label>Score</template>
							<template #value>{{ policy.score }}%</template>
						</Badge>
					</div>

					<div class="policy-name">{{ policy.policy_name }}</div>

					<div class="policy-stats">
						<div class="stat-row">
							<span class="stat-label">Policy ID:</span>
							<span class="stat-value-sm">{{ policy.policy_id }}</span>
						</div>
						<div class="stat-row">
							<span class="stat-label">Agents:</span>
							<span class="stat-value-sm">{{ policy.agentCount.toLocaleString() }}</span>
						</div>
						<div class="stat-row">
							<span class="stat-label">Total Checks:</span>
							<span class="stat-value-sm">{{ policy.total_checks.toLocaleString() }}</span>
						</div>
					</div>

					<!-- Pass/Fail indicator -->
					<div class="compliance-indicator">
						<Badge color="success" size="small">
							<template #value>{{ policy.pass }} Pass</template>
						</Badge>
						<Badge v-if="policy.fail > 0" color="danger" size="small">
							<template #value>{{ policy.fail }} Fail</template>
						</Badge>
					</div>
				</div>
			</div>
		</div>

		<!-- SCA Results List -->
		<n-spin :show="loading">
			<div class="my-3">
				<div v-if="list.length" class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
					<ScaCard v-for="item of list" :key="JSON.stringify(item)" :sca="item" />
				</div>
				<template v-else>
					<n-empty v-if="!loading" description="No SCA results found" class="h-48 justify-center" />
				</template>
			</div>
		</n-spin>

		<div v-if="list.length >= 9" class="flex justify-end">
			<n-pagination
				v-model:page="currentPage"
				v-model:page-size="pageSize"
				:page-slot
				:page-sizes
				:item-count="totalCount"
				:show-size-picker
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ScaOverviewFilter, ScaOverviewFilterTypes } from "./types"
import type { AgentScaOverviewItem, ScaOverviewQuery, ScaOverviewResponse } from "@/types/sca.d"
import { useResizeObserver, useStorage, watchDebounced } from "@vueuse/core"
import axios from "axios"
import _set from "lodash/set"
import _toNumber from "lodash/toSafeInteger"
import {
	NAlert,
	NBadge,
	NButton,
	NEmpty,
	NInput,
	NInputNumber,
	NPagination,
	NPopover,
	NSelect,
	NSpin,
	useMessage
} from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CollapseKeepAlive from "@/components/common/CollapseKeepAlive.vue"
import Icon from "@/components/common/Icon.vue"
import { ScaComplianceLevel } from "@/types/sca.d"
import ListFilters from "./ListFilters.vue"
import ScaCard from "./ScaCard.vue"
import { getComplianceLevel, getComplianceLevelColor } from "./utils"

const loading = ref(false)
const message = useMessage()
const list = ref<AgentScaOverviewItem[]>([])
const pageSizes = [10, 25, 50, 100]
const pageSize = ref(pageSizes[1])
const pageSlot = ref(8)
const showSizePicker = ref(true)
const header = ref()
const showFiltersView = useStorage<boolean>("agents-sca-list-filters-view-state", false, localStorage)

const filtersCTX = ref<{ setFilter: (payload: ScaOverviewFilter[]) => void } | null>(null)
const filters = ref<ScaOverviewFilter[]>([])

const filtered = computed<boolean>(() => {
	return !!filters.value.length
})

const totalCount = ref(0)
const currentPage = ref(1)

const FilterIcon = "carbon:filter-edit"

// Overview data from API response
const overviewData = ref<ScaOverviewResponse | null>(null)

const TotalIcon = "carbon:result"
const ExcellentIcon = "carbon:checkmark-filled"
const GoodIcon = "carbon:checkmark"
const AverageIcon = "carbon:warning-alt"
const PoorIcon = "carbon:warning"
const CriticalIcon = "carbon:warning-filled"
const TopPoliciesIcon = "carbon:trophy"

// Calculate statistics from current data
const stats = computed(() => {
	// Calculate compliance level distribution from current data
	const excellent = list.value.filter(item => getComplianceLevel(item.score) === ScaComplianceLevel.Excellent).length
	const good = list.value.filter(item => getComplianceLevel(item.score) === ScaComplianceLevel.Good).length
	const average = list.value.filter(item => getComplianceLevel(item.score) === ScaComplianceLevel.Average).length
	const poor = list.value.filter(item => getComplianceLevel(item.score) === ScaComplianceLevel.Poor).length
	const critical = list.value.filter(item => getComplianceLevel(item.score) === ScaComplianceLevel.Critical).length

	return {
		excellent,
		good,
		average,
		poor,
		critical
	}
})

// Calculate top policies by compliance score
const topPoliciesByScore = computed(() => {
	// Group policies and calculate averages
	const policyMap = new Map<
		string,
		{
			policy_id: string
			policy_name: string
			score: number
			agentCount: number
			total_checks: number
			pass: number
			fail: number
		}
	>()

	list.value.forEach(item => {
		const key = item.policy_id
		const existing = policyMap.get(key)

		if (existing) {
			// Update averages and counts
			existing.agentCount++
			existing.score = Math.max(existing.score, item.score) // Use highest score for ranking
			existing.total_checks += item.total_checks
			existing.pass += item.pass
			existing.fail += item.fail
		} else {
			policyMap.set(key, {
				policy_id: item.policy_id,
				policy_name: item.policy_name,
				score: item.score,
				agentCount: 1,
				total_checks: item.total_checks,
				pass: item.pass,
				fail: item.fail
			})
		}
	})

	// Convert to array and sort by score
	return Array.from(policyMap.values())
		.sort((a, b) => b.score - a.score)
		.slice(0, 5)
})

function getPercentage(count: number): string {
	if (totalCount.value === 0) return "0"
	return ((count / totalCount.value) * 100).toFixed(1)
}

let abortController: AbortController | null = null

function getList() {
	abortController?.abort()
	abortController = new AbortController()

	loading.value = true

	const query: ScaOverviewQuery = {
		page: currentPage.value,
		page_size: pageSize.value
	}

	for (const key of ["customer_code", "policy_id", "policy_name", "agent_name"] as ScaOverviewFilterTypes[]) {
		if (filters.value.find(o => o.type === key)?.value) {
			_set(query, key, `${filters.value.find(o => o.type === key)?.value}`)
		}
	}
	for (const key of ["min_score", "max_score"] as ScaOverviewFilterTypes[]) {
		if (filters.value.find(o => o.type === key)?.value) {
			_set(query, key, _toNumber(filters.value.find(o => o.type === key)?.value))
		}
	}

	Api.sca
		.searchScaOverview(query, abortController.signal)
		.then(res => {
			loading.value = false

			if (res.data.success) {
				list.value = res.data?.sca_results || []
				totalCount.value = res.data?.total_count || 0
				currentPage.value = res.data?.page || 1
				overviewData.value = res.data
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

function selectPolicyID(value: string) {
	showFiltersView.value = true
	filtersCTX.value?.setFilter([{ type: "policy_id", value }])
}

function selectComplianceLevel(level: ScaComplianceLevel) {
	let min_score = 0
	let max_score = 0

	switch (level) {
		case ScaComplianceLevel.Excellent:
			min_score = 90
			max_score = 100
			break
		case ScaComplianceLevel.Good:
			min_score = 80
			max_score = 89
			break
		case ScaComplianceLevel.Average:
			min_score = 70
			max_score = 79
			break
		case ScaComplianceLevel.Poor:
			min_score = 60
			max_score = 69
			break
		case ScaComplianceLevel.Critical:
			min_score = 0
			max_score = 59
			break
	}

	showFiltersView.value = true
	filtersCTX.value?.setFilter([
		{ type: "min_score", value: min_score },
		{ type: "max_score", value: max_score }
	])
}

function applyFilters(newFilters: ScaOverviewFilter[]) {
	filters.value = newFilters
}

watchDebounced(
	currentPage,
	() => {
		getList()
	},
	{ debounce: 300 }
)

watchDebounced(
	pageSize,
	() => {
		currentPage.value = 1
		getList()
	},
	{ debounce: 300 }
)

watchDebounced(
	filters,
	() => {
		currentPage.value = 1
		getList()
	},
	{ deep: true, debounce: 300, immediate: true }
)

useResizeObserver(header, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	pageSlot.value = width < 700 ? 5 : 8
	showSizePicker.value = width > 550
})
</script>
