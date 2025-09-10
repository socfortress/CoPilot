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
						<div class="flex flex-col gap-2">
							<div class="box">
								Total Vulnerabilities:
								<code>{{ totalCount }}</code>
							</div>
							<div class="box">
								Current Page:
								<code>{{ currentPage }} / {{ totalPages }}</code>
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

const severityOptions = Object.values(VulnerabilitySeverity).map(severity => ({
	label: severity,
	value: severity
}))

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

watchDebounced([selectedCustomer, selectedSeverity, searchCVE, searchAgent, searchPackage], () => {
	currentPage.value = 1
	getList()
}, {
	deep: true,
	debounce: 300,
	immediate: true
})
</script>
