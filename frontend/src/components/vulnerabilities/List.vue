<template>
	<div class="flex flex-col gap-4">
		<!-- Info Banner -->
		<div class="info-banner p-3 rounded-lg border border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/30">
			<div class="flex items-start gap-3">
				<Icon :name="InfoIcon" class="text-blue-600 dark:text-blue-400 mt-0.5" :size="16" />
				<p class="text-sm text-blue-800 dark:text-blue-200 leading-relaxed">
					Vulnerability Overview provides real-time vulnerability data from Wazuh Indexer with EPSS scoring and detailed package information.
				</p>
			</div>
		</div>

		<!-- Statistics Cards -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-4 mb-4">
			<div class="stat-card">
				<div class="stat-header">
					<Icon :name="TotalIcon" :size="20" class="text-blue-600" />
					<span class="stat-title">Total</span>
				</div>
				<div class="stat-value">{{ totalCount.toLocaleString() }}</div>
			</div>

			<div class="stat-card critical">
				<div class="stat-header">
					<Icon :name="CriticalIcon" :size="20" class="text-red-600" />
					<span class="stat-title">Critical</span>
				</div>
				<div class="stat-value">{{ stats.critical.toLocaleString() }}</div>
				<div class="stat-percentage">{{ getPercentage(stats.critical) }}%</div>
			</div>

			<div class="stat-card high">
				<div class="stat-header">
					<Icon :name="HighIcon" :size="20" class="text-orange-600" />
					<span class="stat-title">High</span>
				</div>
				<div class="stat-value">{{ stats.high.toLocaleString() }}</div>
				<div class="stat-percentage">{{ getPercentage(stats.high) }}%</div>
			</div>

			<div class="stat-card medium">
				<div class="stat-header">
					<Icon :name="MediumIcon" :size="20" class="text-yellow-600" />
					<span class="stat-title">Medium</span>
				</div>
				<div class="stat-value">{{ stats.medium.toLocaleString() }}</div>
				<div class="stat-percentage">{{ getPercentage(stats.medium) }}%</div>
			</div>

			<div class="stat-card low">
				<div class="stat-header">
					<Icon :name="LowIcon" :size="20" class="text-blue-600" />
					<span class="stat-title">Low</span>
				</div>
				<div class="stat-value">{{ stats.low.toLocaleString() }}</div>
				<div class="stat-percentage">{{ getPercentage(stats.low) }}%</div>
			</div>
		</div>

		<!-- Quick Stats Row -->
		<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
			<div class="quick-stat">
				<Icon :name="AgentIcon" :size="16" class="text-gray-600" />
				<span class="text-sm text-gray-600 dark:text-gray-400">Affected Agents:</span>
				<span class="font-semibold">{{ stats.uniqueAgents.toLocaleString() }}</span>
			</div>
			<div class="quick-stat">
				<Icon :name="PackageIcon" :size="16" class="text-gray-600" />
				<span class="text-sm text-gray-600 dark:text-gray-400">Packages:</span>
				<span class="font-semibold">{{ stats.uniquePackages.toLocaleString() }}</span>
			</div>
			<div class="quick-stat">
				<Icon :name="CustomerIcon" :size="16" class="text-gray-600" />
				<span class="text-sm text-gray-600 dark:text-gray-400">Customers:</span>
				<span class="font-semibold">{{ stats.uniqueCustomers.toLocaleString() }}</span>
			</div>
		</div>

		<!-- Top 5 Packages by EPSS Score -->
		<div v-if="topEpssPackages.length > 0" class="mb-4">
			<h3 class="text-lg font-semibold mb-3 text-gray-900 dark:text-gray-100 flex items-center gap-2">
				<Icon :name="PackageIcon" :size="20" class="text-orange-600" />
				Top 5 Packages by EPSS Score
			</h3>
			<div class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
				<div
					v-for="(pkg, index) in topEpssPackages.slice(0, 5)"
					:key="`${pkg.package_name}-${pkg.maxEpssScore}`"
					class="epss-package-card clickable"
					:class="{
						'rank-1': index === 0,
						'rank-2': index === 1,
						'rank-3': index === 2,
						'selected': searchPackage === pkg.package_name
					}"
					@click="selectPackage(pkg.package_name)"
				>
					<div class="epss-header">
						<div class="epss-rank">
							<Icon
								:name="index < 3 ? 'carbon:trophy' : 'carbon:warning-alt'"
								:size="16"
								:class="index === 0 ? 'text-yellow-500' : index === 1 ? 'text-gray-400' : index === 2 ? 'text-amber-600' : 'text-orange-500'"
							/>
							<span class="rank-number">#{{ index + 1 }}</span>
						</div>
						<Badge color="warning" type="splitted" size="small">
							<template #label>EPSS</template>
							<template #value>{{ pkg.maxEpssScore.toFixed(3) }}</template>
						</Badge>
					</div>

					<div class="package-name">{{ pkg.package_name }}</div>

					<div class="package-stats">
						<div class="stat-row">
							<span class="stat-label">Vulnerabilities:</span>
							<span class="stat-value">{{ pkg.vulnCount.toLocaleString() }}</span>
						</div>
						<div class="stat-row">
							<span class="stat-label">Affected Agents:</span>
							<span class="stat-value">{{ pkg.affectedAgents.toLocaleString() }}</span>
						</div>
						<div class="stat-row">
							<span class="stat-label">Max CVSS:</span>
							<span class="stat-value">{{ pkg.maxCvssScore?.toFixed(1) || 'N/A' }}</span>
						</div>
					</div>

					<!-- Critical/High severity indicator -->
					<div v-if="pkg.criticalCount > 0 || pkg.highCount > 0" class="severity-indicator">
						<Badge v-if="pkg.criticalCount > 0" color="danger" size="small">
							<template #value>{{ pkg.criticalCount }} Critical</template>
						</Badge>
						<Badge v-if="pkg.highCount > 0" color="warning" size="small">
							<template #value>{{ pkg.highCount }} High</template>
						</Badge>
					</div>
				</div>
			</div>
		</div>

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
							<div class="font-medium text-sm mb-2">Vulnerability Overview</div>

							<div class="grid grid-cols-2 gap-3 text-xs">
								<div class="flex justify-between">
									<span>Total Vulnerabilities:</span>
									<code class="font-mono">{{ totalCount.toLocaleString() }}</code>
								</div>
								<div class="flex justify-between">
									<span>Current Page:</span>
									<code class="font-mono">{{ currentPage }} / {{ totalPages }}</code>
								</div>
							</div>

							<div class="border-t pt-2">
								<div class="text-xs font-medium mb-2">Severity Distribution</div>
								<div class="grid grid-cols-2 gap-2 text-xs">
									<div class="flex justify-between">
										<span class="text-red-600">Critical:</span>
										<span class="font-mono">{{ stats.critical.toLocaleString() }} ({{ getPercentage(stats.critical) }}%)</span>
									</div>
									<div class="flex justify-between">
										<span class="text-orange-600">High:</span>
										<span class="font-mono">{{ stats.high.toLocaleString() }} ({{ getPercentage(stats.high) }}%)</span>
									</div>
									<div class="flex justify-between">
										<span class="text-yellow-600">Medium:</span>
										<span class="font-mono">{{ stats.medium.toLocaleString() }} ({{ getPercentage(stats.medium) }}%)</span>
									</div>
									<div class="flex justify-between">
										<span class="text-blue-600">Low:</span>
										<span class="font-mono">{{ stats.low.toLocaleString() }} ({{ getPercentage(stats.low) }}%)</span>
									</div>
								</div>
							</div>

							<div class="border-t pt-2">
								<div class="text-xs font-medium mb-2">Coverage</div>
								<div class="space-y-1 text-xs">
									<div class="flex justify-between">
										<span>Affected Agents:</span>
										<span class="font-mono">{{ stats.uniqueAgents.toLocaleString() }}</span>
									</div>
									<div class="flex justify-between">
										<span>Unique Packages:</span>
										<span class="font-mono">{{ stats.uniquePackages.toLocaleString() }}</span>
									</div>
									<div class="flex justify-between">
										<span>Customer Codes:</span>
										<span class="font-mono">{{ stats.uniqueCustomers.toLocaleString() }}</span>
									</div>
								</div>
							</div>
						</div>
					</n-popover>					<n-select
						v-model:value="selectedCustomer"
						:options="customerOptions"
						clearable
						size="small"
						placeholder="Customer"
						class="max-w-32"
					/>

					<n-select
						v-model:value="selectedSeverity"
						:options="severityOptions"
						clearable
						size="small"
						placeholder="Severity"
						class="max-w-32"
					/>

					<n-input
						v-model:value="searchCVE"
						size="small"
						placeholder="Search CVE..."
						class="max-w-40"
						clearable
					>
						<template #prefix>
							<Icon :name="SearchIcon"></Icon>
						</template>
					</n-input>

					<n-input
						v-model:value="searchAgent"
						size="small"
						placeholder="Search agent..."
						class="max-w-40"
						clearable
					>
						<template #prefix>
							<Icon :name="HostIcon"></Icon>
						</template>
					</n-input>

					<n-input
						v-model:value="searchPackage"
						size="small"
						placeholder="Search package..."
						class="max-w-40"
						clearable
					>
						<template #prefix>
							<Icon :name="PackageIcon"></Icon>
						</template>
					</n-input>
				</div>
			</div>

			<n-spin :show="loading">
				<div class="my-3">
					<template v-if="list.length">
						<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
							<VulnerabilityCard v-for="item of list" :key="`${item.cve_id}-${item.agent_name}`" :vulnerability="item" />
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
						<n-empty v-if="!loading" description="No vulnerabilities found" class="h-48 justify-center" />
					</template>
				</div>
			</n-spin>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { VulnerabilitySearchItem, VulnerabilitySearchQuery } from "@/types/vulnerabilities.d"
import { watchDebounced } from "@vueuse/core"
import axios from "axios"
import { NButton, NEmpty, NInput, NPagination, NPopover, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { VulnerabilitySeverity } from "@/types/vulnerabilities.d"
import VulnerabilityCard from "./VulnerabilityCard.vue"

const loading = ref(false)
const message = useMessage()
const list = ref<VulnerabilitySearchItem[]>([])
const header = ref()
const totalCount = ref(0)
const currentPage = ref(1)
const pageSize = ref(50)
const totalPages = ref(0)
const selectedCustomer = ref<string | null>(null)
const selectedSeverity = ref<VulnerabilitySeverity | null>(null)
const searchCVE = ref<string>("")
const searchAgent = ref<string>("")
const searchPackage = ref<string>("")

const InfoIcon = "carbon:information"
const SearchIcon = "carbon:search"
const HostIcon = "carbon:bare-metal-server"
const PackageIcon = "carbon:package"
const TotalIcon = "carbon:result"
const CriticalIcon = "carbon:warning-filled"
const HighIcon = "carbon:warning"
const MediumIcon = "carbon:warning-alt"
const LowIcon = "carbon:information"
const AgentIcon = "carbon:bare-metal-server"
const CustomerIcon = "carbon:user-multiple"

const severityOptions = Object.values(VulnerabilitySeverity).map(severity => ({
	label: severity,
	value: severity
}))

// Calculate statistics from current data
const stats = computed(() => {
	const critical = list.value.filter(v => v.severity === VulnerabilitySeverity.Critical).length
	const high = list.value.filter(v => v.severity === VulnerabilitySeverity.High).length
	const medium = list.value.filter(v => v.severity === VulnerabilitySeverity.Medium).length
	const low = list.value.filter(v => v.severity === VulnerabilitySeverity.Low).length

	const uniqueAgents = new Set(list.value.map(v => v.agent_name)).size
	const uniquePackages = new Set(list.value.map(v => v.package_name).filter(Boolean)).size
	const uniqueCustomers = new Set(list.value.map(v => v.customer_code).filter(Boolean)).size

	return {
		critical,
		high,
		medium,
		low,
		uniqueAgents,
		uniquePackages,
		uniqueCustomers
	}
})

// Calculate top packages by EPSS score
const topEpssPackages = computed(() => {
	// Group vulnerabilities by package name
	const packageMap = new Map<string, {
		package_name: string
		vulnCount: number
		maxEpssScore: number
		maxCvssScore: number | null
		affectedAgents: Set<string>
		criticalCount: number
		highCount: number
	}>()

	list.value.forEach(vuln => {
		if (!vuln.package_name || !vuln.epss_score) return

		const epssScore = Number.parseFloat(vuln.epss_score)
		if (Number.isNaN(epssScore)) return

		const key = vuln.package_name
		const existing = packageMap.get(key)

		if (existing) {
			existing.vulnCount++
			existing.maxEpssScore = Math.max(existing.maxEpssScore, epssScore)
			if (vuln.base_score) {
				existing.maxCvssScore = Math.max(existing.maxCvssScore || 0, vuln.base_score)
			}
			existing.affectedAgents.add(vuln.agent_name)

			if (vuln.severity === VulnerabilitySeverity.Critical) existing.criticalCount++
			if (vuln.severity === VulnerabilitySeverity.High) existing.highCount++
		} else {
			packageMap.set(key, {
				package_name: vuln.package_name,
				vulnCount: 1,
				maxEpssScore: epssScore,
				maxCvssScore: vuln.base_score || null,
				affectedAgents: new Set([vuln.agent_name]),
				criticalCount: vuln.severity === VulnerabilitySeverity.Critical ? 1 : 0,
				highCount: vuln.severity === VulnerabilitySeverity.High ? 1 : 0
			})
		}
	})

	// Convert to array and sort by max EPSS score
	return Array.from(packageMap.values())
		.map(pkg => ({
			...pkg,
			affectedAgents: pkg.affectedAgents.size
		}))
		.sort((a, b) => b.maxEpssScore - a.maxEpssScore)
		.slice(0, 5)
})

function getPercentage(count: number): string {
	if (totalCount.value === 0) return "0"
	return ((count / totalCount.value) * 100).toFixed(1)
}

// Get unique customers from the loaded vulnerabilities
const customerOptions = computed(() => {
	const customers = [...new Set(list.value.map(vuln => vuln.customer_code).filter(Boolean))] as string[]
	return customers.map(customer => ({
		label: customer,
		value: customer
	}))
})

let abortController: AbortController | null = null

function getList() {
	abortController?.abort()
	abortController = new AbortController()

	loading.value = true

	const query: VulnerabilitySearchQuery = {
		page: currentPage.value,
		page_size: pageSize.value,
		customer_code: selectedCustomer.value || undefined,
		severity: selectedSeverity.value || undefined,
		cve_id: searchCVE.value || undefined,
		agent_name: searchAgent.value || undefined,
		package_name: searchPackage.value || undefined,
		include_epss: true
	}

	Api.vulnerabilities
		.searchVulnerabilities(query, abortController.signal)
		.then(res => {
			loading.value = false

			if (res.data.success) {
				list.value = res.data?.vulnerabilities || []
				totalCount.value = res.data?.total_count || 0
				totalPages.value = res.data?.total_pages || 0
				currentPage.value = res.data?.page || 1
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

function updatePage(page: number) {
	currentPage.value = page
	getList()
}

function updatePageSize(size: number) {
	pageSize.value = size
	currentPage.value = 1
	getList()
}

function selectPackage(packageName: string) {
	// If the same package is already selected, clear the filter
	if (searchPackage.value === packageName) {
		searchPackage.value = ""
	} else {
		// Set the package name in the search filter
		searchPackage.value = packageName
	}
	// Reset to first page when filtering
	currentPage.value = 1
}

watchDebounced([selectedCustomer, selectedSeverity, searchCVE, searchAgent, searchPackage], () => {
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
}

.stat-card.critical {
	border-color: rgb(254 202 202);
	background-color: rgb(254 242 242);
}

.stat-card.high {
	border-color: rgb(254 215 170);
	background-color: rgb(255 247 237);
}

.stat-card.medium {
	border-color: rgb(254 240 138);
	background-color: rgb(254 252 232);
}

.stat-card.low {
	border-color: rgb(191 219 254);
	background-color: rgb(239 246 255);
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

.quick-stat {
	display: flex;
	align-items: center;
	gap: 0.5rem;
	padding: 0.75rem;
	background-color: rgb(249 250 251);
	border-radius: 0.5rem;
}

/* EPSS Package Cards */
.epss-package-card {
	background-color: white;
	border: 1px solid rgb(229 231 235);
	border-radius: 0.5rem;
	padding: 1rem;
	transition: all 0.2s ease;
}

.epss-package-card.clickable {
	cursor: pointer;
}

.epss-package-card:hover {
	border-color: rgb(156 163 175);
	box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
	transform: translateY(-2px);
}

.epss-package-card.selected {
	border-color: rgb(59 130 246);
	background-color: rgb(239 246 255);
	box-shadow: 0 4px 12px -1px rgb(59 130 246 / 0.2);
}

.epss-package-card.rank-1 {
	border-color: rgb(234 179 8);
	background-color: rgb(255 255 255);
}

.epss-package-card.rank-2 {
	border-color: rgb(156 163 175);
	background-color: rgb(255 255 255);
}

.epss-package-card.rank-3 {
	border-color: rgb(217 119 6);
	background-color: rgb(255 255 255);
}

.epss-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 0.75rem;
}

.epss-rank {
	display: flex;
	align-items: center;
	gap: 0.5rem;
}

.rank-number {
	font-weight: 600;
	font-size: 0.875rem;
	color: rgb(75 85 99);
}

.package-name {
	font-weight: 600;
	font-size: 1rem;
	color: rgb(17 24 39);
	margin-bottom: 0.75rem;
	font-family: ui-monospace, SFMono-Regular, "SF Mono", Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

.package-stats {
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

.stat-value {
	font-size: 1rem;
	font-weight: 800;
	color: rgb(255 255 255);
	background-color: rgb(59 130 246);
	padding: 0.375rem 0.75rem;
	border-radius: 0.5rem;
	font-family: ui-monospace, SFMono-Regular, "SF Mono", Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
	text-align: center;
	min-width: 3rem;
	box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
}

.severity-indicator {
	display: flex;
	gap: 0.5rem;
	flex-wrap: wrap;
}

/* Dark mode styles */
html.dark .stat-card {
	background-color: rgb(31 41 55);
	border-color: rgb(75 85 99);
}

html.dark .stat-card.critical {
	border-color: rgb(220 38 38);
	background-color: rgb(127 29 29);
}

html.dark .stat-card.high {
	border-color: rgb(234 88 12);
	background-color: rgb(154 52 18);
}

html.dark .stat-card.medium {
	border-color: rgb(202 138 4);
	background-color: rgb(161 98 7);
}

html.dark .stat-card.low {
	border-color: rgb(59 130 246);
	background-color: rgb(30 64 175);
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

html.dark .quick-stat {
	background-color: rgb(31 41 55);
	color: rgb(243 244 246);
}

/* Dark mode for EPSS Package Cards */
html.dark .epss-package-card {
	background-color: rgb(31 41 55) !important;
	border-color: rgb(75 85 99);
}

html.dark .epss-package-card:hover {
	border-color: rgb(156 163 175);
}

html.dark .epss-package-card.rank-1 {
	border-color: rgb(234 179 8);
	background-color: rgb(31 41 55) !important;
}

html.dark .epss-package-card.rank-2 {
	border-color: rgb(156 163 175);
	background-color: rgb(31 41 55) !important;
}

html.dark .epss-package-card.rank-3 {
	border-color: rgb(217 119 6);
	background-color: rgb(31 41 55) !important;
}

html.dark .rank-number {
	color: rgb(209 213 219);
}

html.dark .package-name {
	color: rgb(243 244 246);
}

html.dark .stat-label {
	color: rgb(156 163 175);
}

html.dark .stat-value {
	color: rgb(255 255 255);
	background-color: rgb(79 70 229);
	box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.3);
}

/* Alternative dark mode selectors for better compatibility */
.dark .stat-card,
[data-theme="dark"] .stat-card {
	background-color: rgb(31 41 55);
	border-color: rgb(75 85 99);
}

.dark .stat-card.critical,
[data-theme="dark"] .stat-card.critical {
	border-color: rgb(220 38 38);
	background-color: rgb(127 29 29);
}

.dark .stat-card.high,
[data-theme="dark"] .stat-card.high {
	border-color: rgb(234 88 12);
	background-color: rgb(154 52 18);
}

.dark .stat-card.medium,
[data-theme="dark"] .stat-card.medium {
	border-color: rgb(202 138 4);
	background-color: rgb(161 98 7);
}

.dark .stat-card.low,
[data-theme="dark"] .stat-card.low {
	border-color: rgb(59 130 246);
	background-color: rgb(30 64 175);
}

.dark .stat-title,
[data-theme="dark"] .stat-title {
	color: rgb(209 213 219);
}

.dark .stat-value,
[data-theme="dark"] .stat-value {
	color: rgb(255 255 255);
}

.dark .stat-percentage,
[data-theme="dark"] .stat-percentage {
	color: rgb(209 213 219);
}

.dark .quick-stat,
[data-theme="dark"] .quick-stat {
	background-color: rgb(31 41 55);
	color: rgb(243 244 246);
}

/* EPSS Package Cards - Alternative dark mode selectors */
.dark .epss-package-card,
[data-theme="dark"] .epss-package-card {
	background-color: rgb(31 41 55) !important;
	border-color: rgb(75 85 99);
}

.dark .epss-package-card.rank-1,
[data-theme="dark"] .epss-package-card.rank-1 {
	border-color: rgb(234 179 8);
	background-color: rgb(31 41 55) !important;
}

.dark .epss-package-card.rank-2,
[data-theme="dark"] .epss-package-card.rank-2 {
	border-color: rgb(156 163 175);
	background-color: rgb(31 41 55) !important;
}

.dark .epss-package-card.rank-3,
[data-theme="dark"] .epss-package-card.rank-3 {
	border-color: rgb(217 119 6);
	background-color: rgb(31 41 55) !important;
}

.dark .epss-package-card:hover,
[data-theme="dark"] .epss-package-card:hover {
	border-color: rgb(156 163 175);
	box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.3);
}

.dark .epss-package-card.selected,
[data-theme="dark"] .epss-package-card.selected {
	border-color: rgb(96 165 250);
	background-color: rgb(30 58 138);
	box-shadow: 0 4px 12px -1px rgb(96 165 250 / 0.3);
}

.dark .package-name,
[data-theme="dark"] .package-name {
	color: rgb(243 244 246);
}

.dark .stat-label,
[data-theme="dark"] .stat-label {
	color: rgb(156 163 175);
}

.dark .stat-value,
[data-theme="dark"] .stat-value {
	color: rgb(255 255 255);
	background-color: rgb(79 70 229);
	box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.3);
}

/* Media query for system dark mode preference */
@media (prefers-color-scheme: dark) {
	.stat-card {
		background-color: rgb(31 41 55);
		border-color: rgb(75 85 99);
	}

	.stat-card.critical {
		border-color: rgb(220 38 38);
		background-color: rgb(127 29 29);
	}

	.stat-card.high {
		border-color: rgb(234 88 12);
		background-color: rgb(154 52 18);
	}

	.stat-card.medium {
		border-color: rgb(202 138 4);
		background-color: rgb(161 98 7);
	}

	.stat-card.low {
		border-color: rgb(59 130 246);
		background-color: rgb(30 64 175);
	}

	.stat-title {
		color: rgb(209 213 219);
	}

	.stat-value {
		color: rgb(255 255 255);
		background-color: rgb(79 70 229);
		box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.3);
	}

	.stat-percentage {
		color: rgb(209 213 219);
	}

	.quick-stat {
		background-color: rgb(31 41 55);
		color: rgb(243 244 246);
	}

	.epss-package-card {
		background-color: rgb(31 41 55) !important;
		border-color: rgb(75 85 99);
	}

	.epss-package-card:hover {
		border-color: rgb(156 163 175);
		box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.3);
	}

	.epss-package-card.selected {
		border-color: rgb(96 165 250);
		background-color: rgb(30 58 138);
		box-shadow: 0 4px 12px -1px rgb(96 165 250 / 0.3);
	}

	.package-name {
		color: rgb(243 244 246);
	}

	.stat-label {
		color: rgb(156 163 175);
	}
}
</style>
