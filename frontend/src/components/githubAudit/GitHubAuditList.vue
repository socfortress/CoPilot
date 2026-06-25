<template>
	<div class="@container flex flex-col gap-8">
		<div class="flex w-full flex-col gap-4">
			<div class="flex flex-col justify-between gap-4 @2xl:flex-row @2xl:items-center">
				<h2 class="text-xl font-semibold">GitHub Audit Configurations</h2>
				<div class="flex flex-wrap items-center gap-x-6 gap-y-2">
					<n-button text @click="showInfo = true">
						<template #icon>
							<Icon :name="InfoIcon" />
						</template>
						Reference Guide
					</n-button>
					<n-button type="primary" @click="openCreateForm">
						<template #icon>
							<Icon :name="AddIcon" />
						</template>
						New Configuration
					</n-button>
				</div>
			</div>

			<div class="flex flex-wrap items-center gap-2">
				<n-select
					v-model:value="filterCustomerCode"
					placeholder="Filter by Customer"
					clearable
					:options="customerOptions"
					:loading="loadingCustomers"
					class="min-w-50 flex-1"
					@update:value="loadConfigs"
				/>
				<n-select
					v-model:value="filterStatus"
					placeholder="Filter by Status"
					clearable
					:options="statusOptions"
					class="min-w-50 flex-1"
					@update:value="loadConfigs"
				/>
				<n-input
					v-model:value="filterOrganization"
					placeholder="Search organization..."
					clearable
					class="min-w-80 flex-1"
					@keyup.enter="loadConfigs"
					@clear="loadConfigs"
				>
					<template #prefix>
						<Icon :name="SearchIcon" />
					</template>
				</n-input>
			</div>
		</div>

		<n-spin :show="loading">
			<div v-if="configs.length === 0 && !loading" class="py-8 text-center">
				<n-empty description="No configurations found">
					<template #extra>
						<n-button type="primary" @click="openCreateForm">Create your first configuration</n-button>
					</template>
				</n-empty>
			</div>

			<div v-else class="grid grid-cols-1 gap-4 @4xl:grid-cols-2">
				<GitHubAuditCard
					v-for="config in configs"
					:key="config.id"
					:config
					@click="openDetail(config)"
					@edit="openEditForm"
					@audit-complete="loadConfigs"
				/>
			</div>
		</n-spin>

		<n-drawer v-model:show="showForm" :width="600" placement="right" class="max-w-[98vw]">
			<n-drawer-content
				:title="selectedConfig ? 'Edit Configuration' : 'New GitHub Audit Configuration'"
				closable
				:native-scrollbar="false"
			>
				<GitHubAuditConfigForm
					v-if="showForm"
					:config="selectedConfig"
					@saved="onConfigSaved"
					@cancel="showForm = false"
				/>
			</n-drawer-content>
		</n-drawer>

		<n-drawer v-model:show="showDetail" :width="800" placement="right" class="max-w-[98vw]">
			<n-drawer-content v-if="selectedConfig" closable :native-scrollbar="false">
				<template #header>
					<div class="flex items-center gap-3">
						<Icon name="codicon:organization" :size="24" />
						<span>{{ selectedConfig.organization }}</span>
						<n-tag v-if="!selectedConfig.enabled" type="warning" size="small">Disabled</n-tag>
					</div>
				</template>

				<GitHubAuditDetail
					:config="selectedConfig"
					@updated="loadConfigs"
					@edit="openEditForm"
					@close="showDetail = false"
				/>
			</n-drawer-content>
		</n-drawer>

		<n-drawer v-model:show="showInfo" :width="700" placement="right" class="max-w-[98vw]">
			<n-drawer-content closable :native-scrollbar="false">
				<template #header>
					<div class="flex items-center gap-3">
						<Icon :name="InfoIcon" :size="24" />
						<span>GitHub Audit Reference Guide</span>
					</div>
				</template>

				<GitHubAuditInfo />
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { GitHubAuditConfig } from "@/types/githubAudit"
import { NButton, NDrawer, NDrawerContent, NEmpty, NInput, NSelect, NSpin, NTag, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import GitHubAuditCard from "./GitHubAuditCard.vue"
import GitHubAuditConfigForm from "./GitHubAuditConfigForm.vue"
import GitHubAuditDetail from "./GitHubAuditDetail.vue"
import GitHubAuditInfo from "./GitHubAuditInfo.vue"

const AddIcon = "ion:add"
const SearchIcon = "ion:search-outline"
const InfoIcon = "ion:information-circle-outline"

const message = useMessage()
const loading = ref(false)
const configs = ref<GitHubAuditConfig[]>([])
const showForm = ref(false)
const showDetail = ref(false)
const showInfo = ref(false)
const selectedConfig = ref<GitHubAuditConfig | null>(null)

// Filters
const filterCustomerCode = ref<string | null>(null)
const filterStatus = ref<string | null>(null)
const filterOrganization = ref<string | null>(null)
const customerOptions = ref<{ label: string; value: string }[]>([])
const loadingCustomers = ref(false)

const statusOptions = [
	{ label: "Enabled", value: "enabled" },
	{ label: "Disabled", value: "disabled" }
]

async function loadCustomers() {
	if (loadingCustomers.value) return

	loadingCustomers.value = true
	try {
		const response = await Api.customers.getCustomers()
		if (response.data.customers) {
			customerOptions.value = response.data.customers.map((c: any) => ({
				label: `${c.customer_name} (${c.customer_code})`,
				value: c.customer_code
			}))
		}
	} catch (error) {
		console.error("Failed to load customers:", error)
	} finally {
		loadingCustomers.value = false
	}
}

async function loadConfigs() {
	if (loading.value) return

	loading.value = true
	try {
		const response = await Api.githubAudit.getConfigs(filterCustomerCode.value || undefined)
		if (response.data.configs) {
			let filteredConfigs = response.data.configs

			if (filterStatus.value) {
				const isEnabled = filterStatus.value === "enabled"
				filteredConfigs = filteredConfigs.filter((c: GitHubAuditConfig) => c.enabled === isEnabled)
			}

			if (filterOrganization.value) {
				const searchTerm = filterOrganization.value.toLowerCase()
				filteredConfigs = filteredConfigs.filter((c: GitHubAuditConfig) =>
					c.organization.toLowerCase().includes(searchTerm)
				)
			}

			configs.value = filteredConfigs
		}
	} catch (error) {
		message.error(getApiErrorMessage(error as ApiError) || "Failed to load configurations")
		configs.value = []
	} finally {
		loading.value = false
	}
}

function openCreateForm() {
	selectedConfig.value = null
	showForm.value = true
}

function openEditForm(config: GitHubAuditConfig) {
	selectedConfig.value = config
	showDetail.value = false
	showForm.value = true
}

function openDetail(config: GitHubAuditConfig) {
	selectedConfig.value = config
	showDetail.value = true
}

function onConfigSaved() {
	showForm.value = false
	loadConfigs()
}

onBeforeMount(() => {
	loadCustomers()
	loadConfigs()
})
</script>
