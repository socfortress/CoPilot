<template>
	<div class="github-audit-list">
		<n-card>
			<div class="flex justify-between items-center mb-4">
				<h2 class="text-xl font-semibold m-0">GitHub Audit Configurations</h2>
				<n-button type="primary" @click="openCreateForm">
					<template #icon>
						<Icon :name="AddIcon" :size="16" />
					</template>
					New Configuration
				</n-button>
			</div>

			<div class="github-audit-filters flex gap-4 flex-wrap items-center mb-4">
				<n-select
					v-model:value="filterCustomerCode"
					placeholder="Filter by Customer"
					clearable
					:options="customerOptions"
					:loading="loadingCustomers"
					style="min-width: 200px"
					@update:value="loadConfigs"
				/>
				<n-select
					v-model:value="filterStatus"
					placeholder="Filter by Status"
					clearable
					:options="statusOptions"
					style="min-width: 150px"
					@update:value="loadConfigs"
				/>
				<n-input
					v-model:value="filterOrganization"
					placeholder="Search organization..."
					clearable
					style="min-width: 200px"
					@keyup.enter="loadConfigs"
					@clear="loadConfigs"
				>
					<template #prefix>
						<Icon :name="SearchIcon" :size="16" />
					</template>
				</n-input>
			</div>

			<n-spin :show="loading">
				<div v-if="configs.length === 0 && !loading" class="text-center py-8">
					<n-empty description="No configurations found">
						<template #extra>
							<n-button type="primary" @click="openCreateForm">Create your first configuration</n-button>
						</template>
					</n-empty>
				</div>

				<n-grid v-else :cols="2" :x-gap="16" :y-gap="16">
					<n-gi v-for="config in configs" :key="config.id">
						<GitHubAuditCard
							:config="config"
							@click="openDetail(config)"
							@edit="openEditForm"
							@audit-complete="loadConfigs"
						/>
					</n-gi>
				</n-grid>
			</n-spin>
		</n-card>

		<GitHubAuditConfigForm
			v-if="showForm"
			v-model:show="showForm"
			:config="selectedConfig"
			@saved="onConfigSaved"
		/>

		<GitHubAuditDetail
			v-if="showDetail"
			v-model:show="showDetail"
			:config="selectedConfig"
			@updated="loadConfigs"
			@edit="openEditForm"
		/>
	</div>
</template>

<script setup lang="ts">
import type { GitHubAuditConfig } from "@/types/githubAudit.d"
import { NButton, NCard, NEmpty, NGi, NGrid, NInput, NSelect, NSpin, useMessage } from "naive-ui"
import { onMounted, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import GitHubAuditCard from "./GitHubAuditCard.vue"
import GitHubAuditConfigForm from "./GitHubAuditConfigForm.vue"
import GitHubAuditDetail from "./GitHubAuditDetail.vue"

const AddIcon = "ion:add"
const SearchIcon = "ion:search-outline"

const message = useMessage()
const loading = ref(false)
const configs = ref<GitHubAuditConfig[]>([])
const showForm = ref(false)
const showDetail = ref(false)
const selectedConfig = ref<GitHubAuditConfig | null>(null)

// Filters - inline instead of separate component
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
        const response = await Api.githubAudit.getConfigs({
            customerCode: filterCustomerCode.value || undefined,
            enabled: filterStatus.value === "enabled"
? true :
                     filterStatus.value === "disabled" ? false : undefined,
            organization: filterOrganization.value || undefined
        })
        configs.value = response.data.configs || []
    } catch (error: any) {
        message.error(error.response?.data?.detail || "Failed to load configurations")
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

onMounted(() => {
    loadCustomers()
    loadConfigs()
})
</script>
