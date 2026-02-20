<template>
	<div class="flex flex-col gap-4">
		<n-alert type="info">
			CoPilot Searches provides pre-built detection queries for threat hunting in your Wazuh indexer. See
			<a href="https://github.com/socfortress/CoPilot-Search-Queries" target="_blank">
				https://github.com/socfortress/CoPilot-Search-Queries
			</a>
			for details.
		</n-alert>

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

					<n-select
						v-model:value="selectedPlatform"
						:options="platformOptions"
						size="small"
						placeholder="Platform"
						class="max-w-30"
						:consistent-menu-width="false"
					/>

					<n-select
						v-model:value="selectedSeverity"
						:options="severityOptions"
						clearable
						size="small"
						placeholder="Severity"
						class="max-w-30"
						:consistent-menu-width="false"
					/>

					<n-select
						v-model:value="selectedStatus"
						:options="statusOptions"
						clearable
						size="small"
						placeholder="Status"
						class="max-w-30"
						:consistent-menu-width="false"
					/>

					<n-input
						v-model:value="searchQuery"
						size="small"
						placeholder="Search rules..."
						class="max-w-120!"
						clearable
					>
						<template #prefix>
							<Icon :name="SearchIcon" />
						</template>
					</n-input>
				</div>

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
					<div v-if="list.length" class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
						<RuleCard v-for="rule of list" :key="rule.id" :rule="rule" />
					</div>

					<template v-else>
						<n-empty v-if="!loading" description="No rules found" class="h-48 justify-center" />
					</template>
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
	</div>
</template>

<script setup lang="ts">
import type { PlatformFilter, RuleListQuery, RuleSeverity, RuleStatus, RuleSummary } from "@/types/copilotSearches.d"
import { watchDebounced } from "@vueuse/core"
import axios from "axios"
import { NAlert, NButton, NEmpty, NInput, NPagination, NPopover, NSelect, NSpin, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import RuleCard from "./RuleCard.vue"

const loading = ref(false)
const refreshing = ref(false)
const message = useMessage()
const list = ref<RuleSummary[]>([])
const pagination = ref({
	current: 1,
	size: 24,
	total: 0,
	filtered: 0
})

const selectedPlatform = ref<PlatformFilter>("all")
const selectedSeverity = ref<RuleSeverity | null>(null)
const selectedStatus = ref<RuleStatus | null>(null)
const searchQuery = ref<string | null>(null)

const InfoIcon = "carbon:information"
const SearchIcon = "carbon:search"
const RefreshIcon = "carbon:refresh"

const platformOptions = [
	{ label: "All Platforms", value: "all" },
	{ label: "Linux", value: "linux" },
	{ label: "Windows", value: "windows" }
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
		search: searchQuery.value || undefined
	}

	Api.copilotSearches
		.getRules(query, abortController.signal)
		.then(res => {
			loading.value = false

			if (res.data.success) {
				list.value = res.data?.rules || []
				pagination.value.total = res.data?.total || 0
				pagination.value.filtered = res.data?.filtered || 0
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
	} catch (err: any) {
		message.error(err.response?.data?.message || "Failed to refresh cache")
	} finally {
		refreshing.value = false
	}
}

watchDebounced(
	[selectedPlatform, selectedSeverity, selectedStatus, searchQuery, () => pagination.value.current],
	getList,
	{
		deep: true,
		debounce: 300,
		immediate: true
	}
)
</script>
