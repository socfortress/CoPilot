<template>
	<div class="flex flex-col gap-4">
		<!-- Info Banner -->
		<div class="info-banner p-3 rounded-lg border border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/30">
			<div class="flex items-start gap-3">
				<Icon :name="InfoIcon" class="text-blue-600 dark:text-blue-400 mt-0.5" :size="16" />
				<p class="text-sm text-blue-800 dark:text-blue-200 leading-relaxed">
					SCA Overview provides real-time Security Configuration Assessment results from Wazuh Manager across all agents with comprehensive compliance scoring.
				</p>
			</div>
		</div>

		<!-- Filters -->
		<div class="flex flex-col">
			<div ref="header" class="header flex items-center justify-end gap-2">
				<div class="info flex grow gap-2">
					<n-popover overlap placement="bottom-start">
						<template #trigger>
							<div class="bg-default rounded-lg">
								<n-button size="small" class="!cursor-help">
									<template #icon>
										<Icon :name="InfoIcon"></Icon>
									</template>
								</n-button>
							</div>
						</template>
						<div class="flex flex-col gap-3 p-2 max-w-sm">
							<div class="font-medium text-sm mb-2">SCA Overview</div>

							<div class="grid grid-cols-2 gap-3 text-xs">
								<div class="flex justify-between">
									<span>Total Policies:</span>
									<code class="font-mono">{{ totalCount.toLocaleString() }}</code>
								</div>
								<div class="flex justify-between">
									<span>Current Page:</span>
									<code class="font-mono">{{ currentPage }} / {{ totalPages }}</code>
								</div>
							</div>

							<div class="border-t pt-2">
								<div class="text-xs font-medium mb-2">Compliance Distribution</div>
								<div class="grid grid-cols-2 gap-2 text-xs">
									<div class="flex justify-between">
										<span class="text-green-600">Excellent:</span>
										<span class="font-mono">{{ stats.excellent.toLocaleString() }} ({{ getPercentage(stats.excellent) }}%)</span>
									</div>
									<div class="flex justify-between">
										<span class="text-blue-600">Good:</span>
										<span class="font-mono">{{ stats.good.toLocaleString() }} ({{ getPercentage(stats.good) }}%)</span>
									</div>
									<div class="flex justify-between">
										<span class="text-yellow-600">Average:</span>
										<span class="font-mono">{{ stats.average.toLocaleString() }} ({{ getPercentage(stats.average) }}%)</span>
									</div>
									<div class="flex justify-between">
										<span class="text-orange-600">Poor:</span>
										<span class="font-mono">{{ stats.poor.toLocaleString() }} ({{ getPercentage(stats.poor) }}%)</span>
									</div>
									<div class="flex justify-between">
										<span class="text-red-600">Critical:</span>
										<span class="font-mono">{{ stats.critical.toLocaleString() }} ({{ getPercentage(stats.critical) }}%)</span>
									</div>
								</div>
							</div>

							<div class="border-t pt-2">
								<div class="text-xs font-medium mb-2">Coverage</div>
								<div class="space-y-1 text-xs">
									<div class="flex justify-between">
										<span>Agents:</span>
										<span class="font-mono">{{ overviewData?.total_agents?.toLocaleString() || 0 }}</span>
									</div>
									<div class="flex justify-between">
										<span>Policies:</span>
										<span class="font-mono">{{ overviewData?.total_policies?.toLocaleString() || 0 }}</span>
									</div>
									<div class="flex justify-between">
										<span>Avg Score:</span>
										<span class="font-mono">{{ overviewData?.average_score?.toFixed(1) || 0 }}%</span>
									</div>
								</div>
							</div>
						</div>
					</n-popover>

					<n-select
						v-model:value="selectedCustomer"
						:options="customerOptions"
						clearable
						size="small"
						placeholder="Customer"
						class="max-w-32"
						:loading="loadingCustomers"
					/>

					<n-input
						v-model:value="searchPolicyId"
						size="small"
						placeholder="Policy ID..."
						class="max-w-40"
						clearable
					>
						<template #prefix>
							<Icon :name="PolicyIcon"></Icon>
						</template>
					</n-input>

					<n-input
						v-model:value="searchPolicyName"
						size="small"
						placeholder="Policy name..."
						class="max-w-40"
						clearable
					>
						<template #prefix>
							<Icon :name="SearchIcon"></Icon>
						</template>
					</n-input>

					<n-select
						v-model:value="searchAgent"
						:options="agentOptions"
						size="small"
						placeholder="Search agent..."
						class="max-w-40"
						clearable
						filterable
						:loading="loadingAgents"
					/>

					<n-input-number
						v-model:value="minScore"
						size="small"
						placeholder="Min score"
						class="max-w-32"
						:min="0"
						:max="100"
						clearable
					/>

					<n-input-number
						v-model:value="maxScore"
						size="small"
						placeholder="Max score"
						class="max-w-32"
						:min="0"
						:max="100"
						clearable
					/>
				</div>
			</div>
		</div>

		<!-- Statistics Cards -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 gap-4 mb-4">
			<div class="stat-card">
				<div class="stat-header">
					<Icon :name="TotalIcon" :size="20" class="text-blue-600" />
					<span class="stat-title">Total</span>
				</div>
				<div class="stat-value">{{ totalCount.toLocaleString() }}</div>
			</div>

			<div class="stat-card excellent clickable" :class="{ selected: selectedComplianceLevel === ScaComplianceLevel.Excellent }" @click="selectComplianceLevel(ScaComplianceLevel.Excellent)">
				<div class="stat-header">
					<Icon :name="ExcellentIcon" :size="20" class="text-green-600" />
					<span class="stat-title">Excellent</span>
				</div>
				<div class="stat-value">{{ stats.excellent.toLocaleString() }}</div>
				<div class="stat-percentage">{{ getPercentage(stats.excellent) }}%</div>
			</div>

			<div class="stat-card good clickable" :class="{ selected: selectedComplianceLevel === ScaComplianceLevel.Good }" @click="selectComplianceLevel(ScaComplianceLevel.Good)">
				<div class="stat-header">
					<Icon :name="GoodIcon" :size="20" class="text-blue-600" />
					<span class="stat-title">Good</span>
				</div>
				<div class="stat-value">{{ stats.good.toLocaleString() }}</div>
				<div class="stat-percentage">{{ getPercentage(stats.good) }}%</div>
			</div>

			<div class="stat-card average clickable" :class="{ selected: selectedComplianceLevel === ScaComplianceLevel.Average }" @click="selectComplianceLevel(ScaComplianceLevel.Average)">
				<div class="stat-header">
					<Icon :name="AverageIcon" :size="20" class="text-yellow-600" />
					<span class="stat-title">Average</span>
				</div>
				<div class="stat-value">{{ stats.average.toLocaleString() }}</div>
				<div class="stat-percentage">{{ getPercentage(stats.average) }}%</div>
			</div>

			<div class="stat-card poor clickable" :class="{ selected: selectedComplianceLevel === ScaComplianceLevel.Poor }" @click="selectComplianceLevel(ScaComplianceLevel.Poor)">
				<div class="stat-header">
					<Icon :name="PoorIcon" :size="20" class="text-orange-600" />
					<span class="stat-title">Poor</span>
				</div>
				<div class="stat-value">{{ stats.poor.toLocaleString() }}</div>
				<div class="stat-percentage">{{ getPercentage(stats.poor) }}%</div>
			</div>

			<div class="stat-card critical clickable" :class="{ selected: selectedComplianceLevel === ScaComplianceLevel.Critical }" @click="selectComplianceLevel(ScaComplianceLevel.Critical)">
				<div class="stat-header">
					<Icon :name="CriticalIcon" :size="20" class="text-red-600" />
					<span class="stat-title">Critical</span>
				</div>
				<div class="stat-value">{{ stats.critical.toLocaleString() }}</div>
				<div class="stat-percentage">{{ getPercentage(stats.critical) }}%</div>
			</div>
		</div>

		<!-- Top 5 Policies by Compliance Score -->
		<div v-if="topPoliciesByScore.length > 0" class="mb-4">
			<h3 class="text-lg font-semibold mb-3 text-gray-900 dark:text-gray-100 flex items-center gap-2">
				<Icon :name="TopPoliciesIcon" :size="20" class="text-green-600" />
				Top 5 Policies by Compliance Score
			</h3>
			<div class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
				<div
					v-for="(policy, index) in topPoliciesByScore.slice(0, 5)"
					:key="`${policy.policy_id}-${policy.score}`"
					class="policy-card clickable"
					:class="{
						'rank-1': index === 0,
						'rank-2': index === 1,
						'rank-3': index === 2,
						'selected': searchPolicyId === policy.policy_id
					}"
					@click="selectPolicy(policy.policy_id)"
				>
					<div class="policy-header">
						<div class="policy-rank">
							<Icon
								:name="index < 3 ? 'carbon:trophy' : 'carbon:security'"
								:size="16"
								:class="index === 0 ? 'text-yellow-500' : index === 1 ? 'text-gray-400' : index === 2 ? 'text-amber-600' : 'text-green-500'"
							/>
							<span class="rank-number">#{{ index + 1 }}</span>
						</div>
						<Badge :color="getComplianceLevelColor(getComplianceLevel(policy.score))" type="splitted" size="small">
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
				<template v-if="list.length">
					<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
						<ScaCard v-for="item of list" :key="`${item.policy_id}-${item.agent_name}`" :sca="item" />
					</div>

					<!-- Pagination -->
					<div class="flex justify-center mt-6">
						<n-pagination
							v-model:page="currentPage"
							:page-count="totalPages"
							:page-size="pageSize"
							:item-count="totalCount"
							show-size-picker
							:page-sizes="[25, 50, 100, 200]"
							@update:page="updatePage"
							@update:page-size="updatePageSize"
						/>
					</div>
				</template>
				<template v-else>
					<n-empty v-if="!loading" description="No SCA results found" class="h-48 justify-center" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { Agent } from "@/types/agents.d"
import type { Customer } from "@/types/customers.d"
import type { AgentScaOverviewItem, ScaOverviewQuery, ScaOverviewResponse } from "@/types/sca.d"
import { watchDebounced } from "@vueuse/core"
import axios from "axios"
import { NButton, NEmpty, NInput, NInputNumber, NPagination, NPopover, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, onMounted, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getComplianceLevel, getComplianceLevelColor, ScaComplianceLevel } from "@/types/sca.d"
import ScaCard from "./ScaCard.vue"

const loading = ref(false)
const message = useMessage()
const list = ref<AgentScaOverviewItem[]>([])
const header = ref()
const totalCount = ref(0)
const currentPage = ref(1)
const pageSize = ref(50)
const totalPages = ref(0)
const selectedCustomer = ref<string | null>(null)
const selectedComplianceLevel = ref<ScaComplianceLevel | null>(null)
const searchPolicyId = ref<string>("")
const searchPolicyName = ref<string>("")
const searchAgent = ref<string>("")
const minScore = ref<number | null>(null)
const maxScore = ref<number | null>(null)

// Overview data from API response
const overviewData = ref<ScaOverviewResponse | null>(null)

// Agents data for dropdown
const agents = ref<Agent[]>([])
const loadingAgents = ref(false)

// Customers data for dropdown
const customers = ref<Customer[]>([])
const loadingCustomers = ref(false)

const InfoIcon = "carbon:information"
const SearchIcon = "carbon:search"
const PolicyIcon = "carbon:security"
const TotalIcon = "carbon:result"
const ExcellentIcon = "carbon:checkmark-filled"
const GoodIcon = "carbon:checkmark"
const AverageIcon = "carbon:warning-alt"
const PoorIcon = "carbon:warning"
const CriticalIcon = "carbon:warning-filled"
const TopPoliciesIcon = "carbon:trophy"

// Agent options for dropdown
const agentOptions = computed(() => {
	return (agents.value || []).map(agent => ({
		label: agent.hostname,
		value: agent.hostname
	}))
})

// Customer options for dropdown
const customerOptions = computed(() => {
	return (customers.value || []).map(customer => ({
		label: customer.customer_code,
		value: customer.customer_code
	}))
})

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
	const policyMap = new Map<string, {
		policy_id: string
		policy_name: string
		score: number
		agentCount: number
		total_checks: number
		pass: number
		fail: number
	}>()

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
		page_size: pageSize.value,
		customer_code: selectedCustomer.value || undefined,
		policy_id: searchPolicyId.value || undefined,
		policy_name: searchPolicyName.value || undefined,
		agent_name: searchAgent.value || undefined,
		min_score: minScore.value || undefined,
		max_score: maxScore.value || undefined
	}

	// Apply compliance level filter by converting to score range
	if (selectedComplianceLevel.value) {
		switch (selectedComplianceLevel.value) {
			case ScaComplianceLevel.Excellent:
				query.min_score = 90
				query.max_score = 100
				break
			case ScaComplianceLevel.Good:
				query.min_score = 80
				query.max_score = 89
				break
			case ScaComplianceLevel.Average:
				query.min_score = 70
				query.max_score = 79
				break
			case ScaComplianceLevel.Poor:
				query.min_score = 60
				query.max_score = 69
				break
			case ScaComplianceLevel.Critical:
				query.min_score = 0
				query.max_score = 59
				break
		}
	}

	Api.sca
		.searchScaOverview(query, abortController.signal)
		.then(res => {
			loading.value = false

			if (res.data.success) {
				list.value = res.data?.sca_results || []
				totalCount.value = res.data?.total_count || 0
				totalPages.value = res.data?.total_pages || 0
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

function getAgents() {
	loadingAgents.value = true

	Api.agents
		.getAgents()
		.then(res => {
			if (res.data.success) {
				agents.value = res.data.agents || []
			} else {
				message.warning(res.data?.message || "Failed to load agents.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "Failed to load agents.")
		})
		.finally(() => {
			loadingAgents.value = false
		})
}

function getCustomers() {
	loadingCustomers.value = true

	Api.customers
		.getCustomers()
		.then(res => {
			if (res.data.success) {
				customers.value = res.data.customers || []
			} else {
				message.warning(res.data?.message || "Failed to load customers.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "Failed to load customers.")
		})
		.finally(() => {
			loadingCustomers.value = false
		})
}

function updatePage(page: number) {
	currentPage.value = page
	getList()
}

function updatePageSize(size: number) {
	pageSize.value = size
	currentPage.value = 1
	getList()
}

function selectPolicy(policyId: string) {
	// If the same policy is already selected, clear the filter
	if (searchPolicyId.value === policyId) {
		searchPolicyId.value = ""
	} else {
		// Set the policy ID in the search filter
		searchPolicyId.value = policyId
	}
	// Reset to first page when filtering
	currentPage.value = 1
}

function selectComplianceLevel(level: ScaComplianceLevel) {
	// If the same level is already selected, clear the filter
	if (selectedComplianceLevel.value === level) {
		selectedComplianceLevel.value = null
	} else {
		// Set the compliance level filter
		selectedComplianceLevel.value = level
	}
	// Reset to first page when filtering
	currentPage.value = 1
}

// Load agents and customers when component mounts
onMounted(() => {
	getAgents()
	getCustomers()
})

watchDebounced([selectedCustomer, selectedComplianceLevel, searchPolicyId, searchPolicyName, searchAgent, minScore, maxScore], () => {
	currentPage.value = 1
	getList()
}, {
	deep: true,
	debounce: 300,
	immediate: true
})
</script>

<style scoped>
.stat-card {
	background-color: white;
	border-radius: 0.5rem;
	padding: 1rem;
	border: 1px solid rgb(229 231 235);
	box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05);
	transition: all 0.2s ease;
}

.stat-card.clickable {
	cursor: pointer;
}

.stat-card:hover {
	transform: translateY(-2px);
	box-shadow: 0 4px 8px 0 rgb(0 0 0 / 0.1);
}

.stat-card.selected {
	border-width: 2px;
	box-shadow: 0 4px 12px 0 rgb(59 130 246 / 0.3);
}

.stat-card.excellent {
	border-color: rgb(34 197 94);
	background-color: rgb(240 253 244);
}

.stat-card.excellent.selected {
	border-color: rgb(34 197 94);
	background-color: rgb(220 252 231);
}

.stat-card.good {
	border-color: rgb(59 130 246);
	background-color: rgb(239 246 255);
}

.stat-card.good.selected {
	border-color: rgb(59 130 246);
	background-color: rgb(219 234 254);
}

.stat-card.average {
	border-color: rgb(234 179 8);
	background-color: rgb(254 252 232);
}

.stat-card.average.selected {
	border-color: rgb(234 179 8);
	background-color: rgb(254 249 195);
}

.stat-card.poor {
	border-color: rgb(249 115 22);
	background-color: rgb(255 247 237);
}

.stat-card.poor.selected {
	border-color: rgb(249 115 22);
	background-color: rgb(255 237 213);
}

.stat-card.critical {
	border-color: rgb(239 68 68);
	background-color: rgb(254 242 242);
}

.stat-card.critical.selected {
	border-color: rgb(239 68 68);
	background-color: rgb(254 226 226);
}

.stat-header {
	display: flex;
	align-items: center;
	gap: 0.5rem;
	margin-bottom: 0.5rem;
}

.stat-title {
	font-size: 0.875rem;
	font-weight: 500;
	color: rgb(75 85 99);
}

.stat-value {
	font-size: 1.5rem;
	font-weight: 700;
	color: rgb(17 24 39);
}

.stat-percentage {
	font-size: 0.75rem;
	color: rgb(107 114 128);
	margin-top: 0.25rem;
}

/* Policy Cards */
.policy-card {
	background-color: white;
	border: 1px solid rgb(229 231 235);
	border-radius: 0.5rem;
	padding: 1rem;
	transition: all 0.2s ease;
}

.policy-card.clickable {
	cursor: pointer;
}

.policy-card:hover {
	border-color: rgb(156 163 175);
	box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
	transform: translateY(-2px);
}

.policy-card.selected {
	border-color: rgb(59 130 246);
	background-color: rgb(239 246 255);
	box-shadow: 0 4px 12px -1px rgb(59 130 246 / 0.2);
}

.policy-card.rank-1 {
	border-color: rgb(234 179 8);
	background-color: rgb(255 255 255);
}

.policy-card.rank-2 {
	border-color: rgb(156 163 175);
	background-color: rgb(255 255 255);
}

.policy-card.rank-3 {
	border-color: rgb(217 119 6);
	background-color: rgb(255 255 255);
}

.policy-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 0.75rem;
}

.policy-rank {
	display: flex;
	align-items: center;
	gap: 0.5rem;
}

.rank-number {
	font-weight: 600;
	font-size: 0.875rem;
	color: rgb(75 85 99);
}

.policy-name {
	font-weight: 600;
	font-size: 1rem;
	color: rgb(17 24 39);
	margin-bottom: 0.75rem;
	font-family: ui-monospace, SFMono-Regular, "SF Mono", Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

.policy-stats {
	display: flex;
	flex-direction: column;
	gap: 0.5rem;
	margin-bottom: 0.75rem;
}

.stat-row {
	display: flex;
	justify-content: space-between;
	align-items: center;
}

.stat-label {
	font-size: 0.75rem;
	color: rgb(107 114 128);
	font-weight: 500;
}

.stat-value-sm {
	font-size: 0.875rem;
	font-weight: 600;
	color: rgb(17 24 39);
	font-family: ui-monospace, SFMono-Regular, "SF Mono", Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

.compliance-indicator {
	display: flex;
	gap: 0.5rem;
	flex-wrap: wrap;
}

/* Dark mode styles */
html.dark .stat-card {
	background-color: rgb(31 41 55);
	border-color: rgb(75 85 99);
}

html.dark .stat-card.excellent {
	border-color: rgb(34 197 94);
	background-color: rgb(20 83 45);
}

html.dark .stat-card.good {
	border-color: rgb(59 130 246);
	background-color: rgb(30 64 175);
}

html.dark .stat-card.average {
	border-color: rgb(234 179 8);
	background-color: rgb(161 98 7);
}

html.dark .stat-card.poor {
	border-color: rgb(249 115 22);
	background-color: rgb(154 52 18);
}

html.dark .stat-card.critical {
	border-color: rgb(239 68 68);
	background-color: rgb(127 29 29);
}

html.dark .stat-title {
	color: rgb(209 213 219);
}

html.dark .stat-value {
	color: rgb(255 255 255);
}

html.dark .stat-percentage {
	color: rgb(209 213 219);
}

html.dark .policy-card {
	background-color: rgb(31 41 55);
	border-color: rgb(75 85 99);
}

html.dark .policy-card:hover {
	border-color: rgb(156 163 175);
}

html.dark .policy-card.selected {
	border-color: rgb(96 165 250);
	background-color: rgb(30 58 138);
	box-shadow: 0 4px 12px -1px rgb(96 165 250 / 0.3);
}

html.dark .policy-name {
	color: rgb(243 244 246);
}

html.dark .stat-label {
	color: rgb(156 163 175);
}

html.dark .stat-value-sm {
	color: rgb(243 244 246);
}
</style>
