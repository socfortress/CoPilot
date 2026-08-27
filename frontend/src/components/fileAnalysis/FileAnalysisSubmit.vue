<template>
	<div class="mx-auto flex w-full flex-col gap-4">
		<div class="flex flex-col gap-1">
			<h2 class="text-lg font-semibold">File analysis</h2>
			<p class="text-secondary text-sm">
				Upload a file or pull one straight off an endpoint. Tier-1 static inspection always runs — the file is
				parsed, never executed — and detonation is opt-in.
			</p>
		</div>

		<!-- Scopes everything on this page: submissions are stamped with it, and both
		     the endpoint list and the history are read per-customer. -->
		<div class="flex items-center gap-2">
			<n-select
				v-model:value="customerCode"
				:options="customerOptions"
				:loading="customersLoading"
				filterable
				clearable
				class="grow"
				placeholder="Select a customer (required)"
				:render-label="renderCustomerLabel"
			/>
			<!-- History is per-customer, so the button has nothing to open until one is
			     picked — it appears with the scope it belongs to rather than sitting
			     there disabled. -->
			<n-button v-if="customerCode" secondary class="shrink-0" @click="openHistory()">
				<template #icon><Icon :name="HistoryIcon" :size="16" /></template>
				Recent analyses
			</n-button>
		</div>

		<AnalysisPhaseOptions v-model:sandbox="sandbox" v-model:vt-mode="vtMode" />

		<n-tabs v-model:value="activeTab" type="line" animated>
			<n-tab-pane name="upload" tab="Analyze a file" display-directive="show:lazy">
				<UploadPanel :customer-code :sandbox :vt-mode @started="onStarted" />
			</n-tab-pane>
			<n-tab-pane name="collect" tab="Collect from an endpoint" display-directive="show:lazy">
				<CollectPanel :customer-code :sandbox :vt-mode @started="onStarted" />
			</n-tab-pane>
		</n-tabs>

		<n-drawer v-model:show="showHistory" :width="640" class="max-w-[90vw]!" placement="right">
			<n-drawer-content title="Recent analyses" closable :native-scrollbar="false">
				<FileAnalysisHistory :customer-code="customerCode || ''" :refresh-key />
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="ts">
import type { SelectOption } from "naive-ui"
import type { VNodeChild } from "vue"
import type { ApiError } from "@/types/common"
import type { Customer } from "@/types/customers"
import type { ReputationMode } from "@/types/file-analysis"
import { NButton, NDrawer, NDrawerContent, NSelect, NTabPane, NTabs, useMessage } from "naive-ui"
import { computed, h, onMounted, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import FileAnalysisHistory from "@/components/fileAnalysis/FileAnalysisHistory.vue"
import AnalysisPhaseOptions from "@/components/fileAnalysis/submit/AnalysisPhaseOptions.vue"
import CollectPanel from "@/components/fileAnalysis/submit/CollectPanel.vue"
import UploadPanel from "@/components/fileAnalysis/submit/UploadPanel.vue"
import { getApiErrorMessage } from "@/utils"

type SubmitTab = "upload" | "collect"

const TABS: SubmitTab[] = ["upload", "collect"]
const LS_CUSTOMER = "fileAnalysis.customerCode"
const HistoryIcon = "carbon:time"

const route = useRoute()
const router = useRouter()
const message = useMessage()

const customerCode = ref<string | null>(null)
const customers = ref<Customer[]>([])
const customersLoading = ref(false)
const refreshKey = ref(0)
const showHistory = ref(false)

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

// Remember the last-used customer across visits. Clearing it closes the drawer:
// the history it is showing belongs to a customer that is no longer selected.
watch(customerCode, val => {
	if (val) localStorage.setItem(LS_CUSTOMER, val)
	else showHistory.value = false
})

// Bump the key on every open so a drawer reopened after a submission shows the
// new analysis instead of the list it was mounted with.
function openHistory() {
	refreshKey.value++
	showHistory.value = true
}

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
	router.push({ name: "FileAnalysisDetails", params: { jobId: jobIds[0] }, query })
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
