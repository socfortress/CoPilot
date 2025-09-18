<template>
	<n-spin :show="loading" content-class="flex flex-col gap-4">
		<!-- Statistics Cards -->
		<div>
			<div class="mb-5 flex flex-wrap items-center justify-between gap-3">
				<h3 class="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
					<Icon name="carbon:chart-ring" :size="20" class="text-primary" />
					Distribution
				</h3>

				<p class="flex items-center gap-2 text-sm">
					Total:
					<code>{{ totalCount.toLocaleString() }}</code>
					<Icon :name="InfoIcon" :size="14" />
				</p>
			</div>
			<div class="grid-auto-fit-250 grid gap-4">
				<n-card
					v-for="item of statisticsCards"
					:key="item.level"
					class="ring-primary cursor-pointer transition-all duration-300 hover:ring-1"
					content-class="flex flex-col gap-2"
					size="small"
					@click="selectComplianceLevel(item.level)"
				>
					<div class="flex items-center justify-between gap-2 whitespace-nowrap">
						<div class="flex items-center gap-2">
							<ScaLevelIcon :level="item.level" :size="24" :class="item.iconClass" />
							<span class="text-xl">{{ item.label }}</span>
						</div>
						<div class="font-mono text-xl font-bold">{{ stats[item.key].toLocaleString() }}</div>
					</div>
					<n-progress
						type="line"
						indicator-placement="inside"
						:percentage="getPercentage(stats[item.key])"
						:color="item.barColor"
						class="custom-progress"
					/>
				</n-card>
			</div>
		</div>

		<!-- Coverage Cards -->
		<div class="mt-8">
			<div class="mb-5 flex flex-wrap items-center justify-between gap-3">
				<h3 class="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
					<Icon name="carbon:double-axis-chart-column" :size="20" class="text-primary" />
					Coverage
				</h3>

				<p class="flex items-center gap-2 text-sm">
					Coverage based on the 100 policies with the lowest score.
					<Icon :name="InfoIcon" :size="14" />
				</p>
			</div>

			<n-card class="bg-secondary! overflow-hidden">
				<div class="flex flex-wrap justify-between gap-8">
					<n-statistic
						label="Agents"
						:value="overviewData?.total_agents?.toLocaleString() || 0"
						tabular-nums
					/>
					<n-statistic
						label="Policies"
						:value="overviewData?.total_policies?.toLocaleString() || 0"
						tabular-nums
					/>
					<n-statistic label="Avg Score" :value="overviewData?.average_score?.toFixed(1) || 0" tabular-nums />
				</div>
			</n-card>
		</div>

		<!-- Top 5 Policies by Compliance Score -->
		<div v-if="topPoliciesByScore.length > 0" class="mt-8">
			<div class="mb-5 flex flex-wrap items-center justify-between gap-3">
				<h3 class="flex items-center gap-2 text-lg font-semibold">
					<Icon :name="TopPoliciesIcon" :size="20" class="text-primary" />
					Top 5 Policies by Compliance Score
				</h3>

				<p class="flex items-center gap-2 text-sm">
					Ranking based on the 100 policies with the lowest score.
					<Icon :name="InfoIcon" :size="14" />
				</p>
			</div>
			<div class="grid-auto-fit-250 grid gap-10">
				<div
					v-for="(policy, index) in topPoliciesByScore"
					:key="policy.policy_id"
					class="@container flex items-stretch gap-2"
				>
					<div class="flex items-end">
						<div
							class="w-4 rounded-b-sm rounded-t-2xl"
							:class="{
								'h-full bg-yellow-500': index === 0,
								'h-8/12 bg-gray-400': index === 1,
								'h-4/12 bg-amber-600': index === 2
							}"
						></div>
					</div>

					<div
						class="bg-secondary ring-primary flex grow cursor-pointer flex-col gap-2 rounded-md px-3 py-2 transition-all duration-300 hover:ring-1"
						@click="selectPolicyID(policy.policy_id)"
					>
						<div class="flex items-center justify-between gap-4">
							<div class="flex items-center gap-2 text-xl">
								<Icon
									:name="index < 3 ? 'carbon:trophy' : 'carbon:warning-alt'"
									:size="20"
									:class="
										index === 0
											? 'text-yellow-500'
											: index === 1
												? 'text-gray-400'
												: index === 2
													? 'text-amber-600'
													: 'text-info'
									"
								/>
								<span>#{{ index + 1 }}</span>
							</div>
							<ScaLevelBadge :score="policy.score" class="mt-1" />
						</div>

						<div class="text-lg font-semibold leading-snug">{{ policy.policy_name }}</div>

						<div class="@md:grid-cols-2 text-secondary grid grid-cols-1 gap-1 break-all text-xs">
							<div class="flex items-center gap-2">
								<span>Policy ID:</span>
								<span class="font-mono font-semibold">{{ policy.policy_id }}</span>
							</div>
							<div class="flex items-center gap-2">
								<span>Agents:</span>
								<span class="font-mono font-semibold">{{ policy.agentCount.toLocaleString() }}</span>
							</div>
							<div class="flex items-center gap-2">
								<span>Total Checks:</span>
								<span class="font-mono font-semibold">
									{{ policy.total_checks.toLocaleString() }}
								</span>
							</div>
							<div class="flex items-center gap-2">
								<span class="text-success">Pass:</span>
								<span class="font-mono font-semibold">
									{{ policy.pass }}
								</span>
							</div>
							<div class="flex items-center gap-2">
								<span class="text-error">Fail:</span>
								<span class="font-mono font-semibold">{{ policy.fail }}</span>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { ScaOverviewFilter, ScaOverviewFilterTypes } from "./types"
import type { AgentScaOverviewItem, ScaOverviewQuery, ScaOverviewResponse } from "@/types/sca.d"
import { watchDebounced } from "@vueuse/core"
import axios from "axios"
import _set from "lodash/set"
import _toNumber from "lodash/toNumber"
import { NCard, NProgress, NSpin, NStatistic, useMessage } from "naive-ui"
import { computed, ref, toRefs } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { ScaComplianceLevel } from "@/types/sca.d"
import ScaLevelBadge from "./ScaLevelBadge.vue"
import ScaLevelIcon from "./ScaLevelIcon.vue"
import { getComplianceLevel } from "./utils"

const props = defineProps<{ filters: ScaOverviewFilter[] }>()

const emit = defineEmits<{
	(e: "update:min_score", value: number): void
	(e: "update:max_score", value: number): void
	(e: "update:policy_id", value: string): void
}>()

const { filters } = toRefs(props)

const loading = ref(false)
const message = useMessage()
const list = ref<AgentScaOverviewItem[]>([])

const totalCount = ref(0)

// Overview data from API response
const overviewData = ref<ScaOverviewResponse | null>(null)

const InfoIcon = "carbon:information"
const TopPoliciesIcon = "carbon:trophy"

// Define the allowed keys for statistics
type LevelKey = "excellent" | "good" | "average" | "poor" | "critical"

const statisticsCards: {
	label: string
	level: ScaComplianceLevel
	iconClass: string
	barColor: string
	key: LevelKey
}[] = [
	{
		label: "Excellent",
		level: ScaComplianceLevel.Excellent,
		iconClass: "text-success",
		barColor: "var(--success-color)",
		key: "excellent"
	},
	{
		label: "Good",
		level: ScaComplianceLevel.Good,
		iconClass: "text-info",
		barColor: "var(--info-color)",
		key: "good"
	},
	{
		label: "Average",
		level: ScaComplianceLevel.Average,
		iconClass: "text-warning",
		barColor: "var(--warning-color)",
		key: "average"
	},
	{
		label: "Poor",
		level: ScaComplianceLevel.Poor,
		iconClass: "text-orange-500",
		barColor: "var(--color-orange-500)",
		key: "poor"
	},
	{
		label: "Critical",
		level: ScaComplianceLevel.Critical,
		iconClass: "text-error",
		barColor: "var(--error-color)",
		key: "critical"
	}
]

// Calculate statistics from current data
const stats = computed((): Record<LevelKey, number> => {
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

function getPercentage(count: number): number {
	if (totalCount.value === 0) return 0
	return _toNumber(((count / totalCount.value) * 100).toFixed(1))
}

let abortController: AbortController | null = null

function getList() {
	abortController?.abort()
	abortController = new AbortController()

	loading.value = true

	const query: ScaOverviewQuery = {
		page: 1,
		page_size: 100
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
	emit("update:policy_id", value)
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

	emit("update:min_score", min_score)
	emit("update:max_score", max_score)
}

watchDebounced(
	filters,
	() => {
		getList()
	},
	{ deep: true, debounce: 300, immediate: true }
)
</script>

<style lang="scss" scoped>
.custom-progress {
	:deep() {
		.n-progress-graph-line-indicator {
			text-shadow:
				0px 0px 1px black,
				0px 0px 2px black,
				0px 0px 3px black;
			font-weight: bold;
			color: white !important;
		}
	}
}
</style>
