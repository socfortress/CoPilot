<template>
	<div class="sca-content">
		<!-- Overview Section -->
		<div class="mb-6">
			<h3 class="text-lg font-semibold mb-3 flex items-center gap-2">
				<Icon :name="OverviewIcon" :size="20" />
				Policy Overview
			</h3>
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<div class="space-y-3">
					<div class="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-gray-800 rounded">
						<span class="text-sm font-medium">Policy ID:</span>
						<code class="text-sm">{{ sca.policy_id }}</code>
					</div>
					<div class="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-gray-800 rounded">
						<span class="text-sm font-medium">Agent:</span>
						<span class="text-sm font-mono">{{ sca.agent_name }}</span>
					</div>
					<div v-if="sca.customer_code" class="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-gray-800 rounded">
						<span class="text-sm font-medium">Customer:</span>
						<Badge class="text-xs">
							<template #value>{{ sca.customer_code }}</template>
						</Badge>
					</div>
				</div>
				<div class="space-y-3">
					<div class="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-gray-800 rounded">
						<span class="text-sm font-medium">Compliance Level:</span>
						<Badge :color="getComplianceLevelColor(getComplianceLevel(sca.score))">
							<template #iconLeft><Icon :name="getComplianceLevelIcon(getComplianceLevel(sca.score))" :size="14" /></template>
							<template #value>{{ getComplianceLevel(sca.score) }}</template>
						</Badge>
					</div>
					<div class="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-gray-800 rounded">
						<span class="text-sm font-medium">Score:</span>
						<Badge color="primary" type="splitted">
							<template #label>Score</template>
							<template #value>{{ sca.score }}%</template>
						</Badge>
					</div>
					<div class="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-gray-800 rounded">
						<span class="text-sm font-medium">Scan Date:</span>
						<span class="text-sm">{{ formatDateTime(sca.end_scan) }}</span>
					</div>
				</div>
			</div>
		</div>

		<!-- Description Section -->
		<div class="mb-6">
			<h3 class="text-lg font-semibold mb-3 flex items-center gap-2">
				<Icon :name="DescriptionIcon" :size="20" />
				Description
			</h3>
			<div class="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
				<p class="text-sm leading-relaxed">{{ sca.description }}</p>
			</div>
		</div>

		<!-- Compliance Statistics -->
		<div class="mb-6">
			<h3 class="text-lg font-semibold mb-3 flex items-center gap-2">
				<Icon :name="StatsIcon" :size="20" />
				Compliance Statistics
			</h3>
			<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
				<div class="stat-card-small pass">
					<div class="stat-header-small">
						<Icon :name="PassIcon" :size="16" class="text-green-600" />
						<span class="stat-title-small">Passed</span>
					</div>
					<div class="stat-value-small">{{ sca.pass_count }}</div>
					<div class="stat-percentage-small">{{ getCheckPercentage(sca.pass_count) }}%</div>
				</div>

				<div class="stat-card-small fail">
					<div class="stat-header-small">
						<Icon :name="FailIcon" :size="16" class="text-red-600" />
						<span class="stat-title-small">Failed</span>
					</div>
					<div class="stat-value-small">{{ sca.fail_count }}</div>
					<div class="stat-percentage-small">{{ getCheckPercentage(sca.fail_count) }}%</div>
				</div>

				<div v-if="sca.invalid_count > 0" class="stat-card-small invalid">
					<div class="stat-header-small">
						<Icon :name="InvalidIcon" :size="16" class="text-yellow-600" />
						<span class="stat-title-small">Invalid</span>
					</div>
					<div class="stat-value-small">{{ sca.invalid_count }}</div>
					<div class="stat-percentage-small">{{ getCheckPercentage(sca.invalid_count) }}%</div>
				</div>

				<div class="stat-card-small total">
					<div class="stat-header-small">
						<Icon :name="TotalIcon" :size="16" class="text-blue-600" />
						<span class="stat-title-small">Total</span>
					</div>
					<div class="stat-value-small">{{ sca.total_checks }}</div>
					<div class="stat-percentage-small">100%</div>
				</div>
			</div>
		</div>

		<!-- Progress Bar -->
		<div class="mb-6">
			<h3 class="text-lg font-semibold mb-3 flex items-center gap-2">
				<Icon :name="ProgressIcon" :size="20" />
				Compliance Progress
			</h3>
			<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-6 relative overflow-hidden">
				<div
					class="bg-green-500 h-6 rounded-full transition-all duration-500 flex items-center justify-end pr-2"
					:style="{ width: `${sca.score}%` }"
				>
					<span v-if="sca.score > 15" class="text-white text-xs font-semibold">{{ sca.score }}%</span>
				</div>
				<span v-if="sca.score <= 15" class="absolute inset-0 flex items-center justify-center text-xs font-semibold text-gray-700 dark:text-gray-300">
					{{ sca.score }}%
				</span>
			</div>
			<div class="flex justify-between text-xs text-gray-500 mt-1">
				<span>0%</span>
				<span>50%</span>
				<span>100%</span>
			</div>
		</div>

		<!-- Scan Information -->
		<div class="mb-6">
			<h3 class="text-lg font-semibold mb-3 flex items-center gap-2">
				<Icon :name="ScanIcon" :size="20" />
				Scan Information
			</h3>
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<div class="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-gray-800 rounded">
					<span class="text-sm font-medium">Scan Started:</span>
					<span class="text-sm">{{ formatDateTime(sca.start_scan) }}</span>
				</div>
				<div class="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-gray-800 rounded">
					<span class="text-sm font-medium">Scan Completed:</span>
					<span class="text-sm">{{ formatDateTime(sca.end_scan) }}</span>
				</div>
				<div v-if="sca.hash_file" class="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-gray-800 rounded">
					<span class="text-sm font-medium">Hash File:</span>
					<code class="text-xs">{{ sca.hash_file }}</code>
				</div>
				<div class="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-gray-800 rounded">
					<span class="text-sm font-medium">Scan Duration:</span>
					<span class="text-sm">{{ getScanDuration() }}</span>
				</div>
			</div>
		</div>

		<!-- References -->
		<div v-if="sca.references" class="mb-6">
			<h3 class="text-lg font-semibold mb-3 flex items-center gap-2">
				<Icon :name="ReferenceIcon" :size="20" />
				References
			</h3>
			<div class="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
				<p class="text-sm leading-relaxed break-all">{{ sca.references }}</p>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { AgentScaOverviewItem } from "@/types/sca.d"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import { getComplianceLevel, getComplianceLevelColor, getComplianceLevelIcon } from "@/types/sca.d"

const { sca } = defineProps<{ sca: AgentScaOverviewItem }>()

const OverviewIcon = "carbon:overview"
const DescriptionIcon = "carbon:document"
const StatsIcon = "carbon:analytics"
const ProgressIcon = "carbon:progress-bar"
const ScanIcon = "carbon:scan"
const ReferenceIcon = "carbon:link"
const PassIcon = "carbon:checkmark-filled"
const FailIcon = "carbon:close-filled"
const InvalidIcon = "carbon:warning-alt"
const TotalIcon = "carbon:result"

function getCheckPercentage(count: number): string {
	if (sca.total_checks === 0) return "0"
	return ((count / sca.total_checks) * 100).toFixed(1)
}

function formatDateTime(dateString: string): string {
	return new Date(dateString).toLocaleString()
}

function getScanDuration(): string {
	const start = new Date(sca.start_scan)
	const end = new Date(sca.end_scan)
	const durationMs = end.getTime() - start.getTime()
	const durationMinutes = Math.floor(durationMs / 60000)
	const durationSeconds = Math.floor((durationMs % 60000) / 1000)

	if (durationMinutes > 0) {
		return `${durationMinutes}m ${durationSeconds}s`
	}
	return `${durationSeconds}s`
}
</script>

<style scoped>
.stat-card-small {
	background-color: white;
	border-radius: 0.5rem;
	padding: 0.75rem;
	border: 1px solid rgb(229 231 235);
	box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05);
}

.stat-card-small.pass {
	border-color: rgb(34 197 94);
	background-color: rgb(240 253 244);
}

.stat-card-small.fail {
	border-color: rgb(239 68 68);
	background-color: rgb(254 242 242);
}

.stat-card-small.invalid {
	border-color: rgb(234 179 8);
	background-color: rgb(254 252 232);
}

.stat-card-small.total {
	border-color: rgb(59 130 246);
	background-color: rgb(239 246 255);
}

.stat-header-small {
	display: flex;
	align-items: center;
	gap: 0.5rem;
	margin-bottom: 0.5rem;
}

.stat-title-small {
	font-size: 0.75rem;
	font-weight: 500;
	color: rgb(75 85 99);
}

.stat-value-small {
	font-size: 1.25rem;
	font-weight: 700;
	color: rgb(17 24 39);
}

.stat-percentage-small {
	font-size: 0.7rem;
	color: rgb(107 114 128);
	margin-top: 0.25rem;
}

/* Dark mode styles */
html.dark .stat-card-small {
	background-color: rgb(31 41 55);
	border-color: rgb(75 85 99);
}

html.dark .stat-card-small.pass {
	border-color: rgb(34 197 94);
	background-color: rgb(20 83 45);
}

html.dark .stat-card-small.fail {
	border-color: rgb(239 68 68);
	background-color: rgb(127 29 29);
}

html.dark .stat-card-small.invalid {
	border-color: rgb(234 179 8);
	background-color: rgb(161 98 7);
}

html.dark .stat-card-small.total {
	border-color: rgb(59 130 246);
	background-color: rgb(30 64 175);
}

html.dark .stat-title-small {
	color: rgb(209 213 219);
}

html.dark .stat-value-small {
	color: rgb(255 255 255);
}

html.dark .stat-percentage-small {
	color: rgb(209 213 219);
}
</style>
