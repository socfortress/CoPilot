<template>
	<div class="mx-auto flex w-full flex-col gap-4">
		<div class="flex flex-col gap-1">
			<h2 class="text-lg font-semibold">File analysis</h2>
			<p class="text-secondary text-sm">
				Upload a file or pull one straight off an endpoint. Tier-1 static inspection always runs — the file is
				parsed, never executed — and detonation is opt-in.
			</p>
		</div>

		<!-- Scopes all three tabs: submissions are stamped with it, and both the
		     endpoint list and the history are read per-customer. -->
		<n-select
			v-model:value="customerCode"
			:options="customerOptions"
			:loading="customersLoading"
			filterable
			clearable
			placeholder="Select a customer (required)"
			:render-label="renderCustomerLabel"
		/>

		<!-- Applies to both submission tabs, and to neither of them on History. -->
		<AnalysisPhaseOptions v-if="activeTab !== 'history'" v-model:sandbox="sandbox" v-model:vt-mode="vtMode" />

		<n-tabs v-model:value="activeTab" type="line" animated>
			<n-tab-pane name="upload" tab="Analyze a file" display-directive="show:lazy">
				<UploadPanel :customer-code :sandbox :vt-mode @started="onStarted" />
			</n-tab-pane>
			<n-tab-pane name="collect" tab="Collect from an endpoint" display-directive="show:lazy">
				<CollectPanel :customer-code :sandbox :vt-mode @started="onStarted" />
			</n-tab-pane>
			<n-tab-pane name="history" tab="Recent analyses" display-directive="show:lazy">
				<FileAnalysisHistory :customer-code="customerCode || ''" :refresh-key />
			</n-tab-pane>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
import type { SelectOption } from "naive-ui"
import type { VNodeChild } from "vue"
import type { ApiError } from "@/types/common"
import type { Customer } from "@/types/customers"
import type { ReputationMode } from "@/types/file-analysis"
import { NSelect, NTabPane, NTabs, useMessage } from "naive-ui"
import { computed, h, onMounted, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import Api from "@/api"
import FileAnalysisHistory from "@/components/fileAnalysis/FileAnalysisHistory.vue"
import AnalysisPhaseOptions from "@/components/fileAnalysis/submit/AnalysisPhaseOptions.vue"
import CollectPanel from "@/components/fileAnalysis/submit/CollectPanel.vue"
import UploadPanel from "@/components/fileAnalysis/submit/UploadPanel.vue"
import { getApiErrorMessage } from "@/utils"

type SubmitTab = "upload" | "collect" | "history"

const TABS: SubmitTab[] = ["upload", "collect", "history"]
const LS_CUSTOMER = "fileAnalysis.customerCode"

const route = useRoute()
const router = useRouter()
const message = useMessage()

const customerCode = ref<string | null>(null)
const customers = ref<Customer[]>([])
const customersLoading = ref(false)
const refreshKey = ref(0)

// Pre-analysis phase selection, shared by both submission tabs.
const sandbox = ref(true)
const vtMode = ref<ReputationMode>("lookup")

// The tab lives in the URL so a reload — or a link handed to a colleague —
// reopens the one that was in use.
const activeTab = ref<SubmitTab>(readTabFromUrl())

const customerOptions = computed<SelectOption[]>(() =>
	customers.value.map(c => ({
		label: c.customer_name,
		value: c.customer_code,
		customer: c
	}))
)

function readTabFromUrl(): SubmitTab {
	const tab = route.query.tab as string
	return TABS.includes(tab as SubmitTab) ? (tab as SubmitTab) : "upload"
}

// replace, not push: flipping a tab must not pile up history entries that the
// back button then has to walk through one by one.
watch(activeTab, tab => {
	if (route.query.tab === tab) return
	router.replace({ query: { ...route.query, tab } })
})

watch(
	() => route.query.tab,
	() => {
		activeTab.value = readTabFromUrl()
	}
)

// Remember the last-used customer across visits.
watch(customerCode, val => {
	if (val) localStorage.setItem(LS_CUSTOMER, val)
})

function renderCustomerLabel(option: SelectOption): VNodeChild {
	const c = option.customer as Customer | undefined
	if (!c) return option.label as string
	return h("div", { class: "flex items-center justify-between gap-3 w-full" }, [
		h("span", c.customer_name),
		h("span", { class: "text-secondary text-xs" }, c.customer_code)
	])
}

// Both submission paths end here, so an upload and a collection land on the
// result view identically.
function onStarted(jobIds: string[]) {
	if (!jobIds.length) return
	refreshKey.value++
	// Carry the whole batch so the result view can show all of them in a sidebar.
	const query = jobIds.length > 1 ? { batch: jobIds.join(",") } : undefined
	router.push({ name: "FileAnalysis", params: { jobId: jobIds[0] }, query })
}

function loadCustomers() {
	customersLoading.value = true
	Api.customers
		.getCustomers({})
		.then(res => {
			if (res.data.success && res.data.customers) {
				customers.value = res.data.customers
				// Restore last-used selection if it still exists.
				const saved = localStorage.getItem(LS_CUSTOMER)
				if (saved && !customerCode.value && customers.value.some(c => c.customer_code === saved)) {
					customerCode.value = saved
				}
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Could not load customers.")
		})
		.finally(() => {
			customersLoading.value = false
		})
}

onMounted(loadCustomers)
</script>
