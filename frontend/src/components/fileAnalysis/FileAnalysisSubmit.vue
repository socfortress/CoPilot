<template>
	<div class="mx-auto flex w-full max-w-2xl flex-col gap-4 py-6">
		<div class="flex flex-col gap-1">
			<h2 class="text-lg font-semibold">Analyze a file</h2>
			<p class="text-secondary text-sm">
				Static inspection runs on the CoPilot host in a locked-down container — the file is parsed, never executed.
				Detonation (if enabled) is opt-in. You can also pull a file straight off an endpoint or from a
				Velociraptor flow's uploads.
			</p>
		</div>

		<n-select
			v-model:value="customerCode"
			:options="customerOptions"
			:loading="customersLoading"
			filterable
			clearable
			placeholder="Select a customer (required)"
			:render-label="renderCustomerLabel"
		/>

		<!-- Phase selection — chosen BEFORE analysis. Tier-1 static always runs. -->
		<div class="border-default flex flex-col gap-3 rounded-lg border p-3">
			<span class="text-secondary text-xs font-medium">Analysis phases</span>

			<div class="flex items-center justify-between gap-4">
				<div class="flex flex-col">
					<span class="text-sm">Sandbox detonation (Tier 2)</span>
					<span class="text-secondary text-xs">
						Run the file in the CAPE VM to observe its behaviour. Off = static inspection only.
					</span>
				</div>
				<n-switch v-model:value="sandbox" />
			</div>

			<div class="flex flex-col gap-1">
				<div class="flex flex-wrap items-center justify-between gap-2">
					<span class="text-sm">VirusTotal</span>
					<n-radio-group v-model:value="vtMode" size="small">
						<n-radio-button value="off">Off</n-radio-button>
						<n-radio-button value="lookup">Hash lookup</n-radio-button>
						<n-radio-button value="upload">Lookup + upload</n-radio-button>
					</n-radio-group>
				</div>
				<span class="text-secondary text-xs">
					<template v-if="vtMode === 'off'">VirusTotal is skipped entirely — nothing about this file is sent.</template>
					<template v-else-if="vtMode === 'lookup'">
						Checks the file's hash only — the file itself is <b>never uploaded</b>.
					</template>
					<template v-else>
						⚠ Uploads the file if VirusTotal hasn't seen it — this <b>publishes it</b> and can't be undone.
					</template>
				</span>
			</div>
		</div>

		<n-upload
			:show-file-list="false"
			:disabled="!customerCode || uploading"
			:custom-request="handleUpload"
			directory-dnd
		>
			<n-upload-dragger>
				<div class="flex flex-col items-center gap-2 py-6">
					<Icon :name="UploadIcon" :size="34" class="text-secondary" />
					<span class="text-sm font-medium">Click or drag a file here to analyze</span>
					<span class="text-secondary text-xs">
						{{ customerCode ? "Uploaded bytes never leave the host by default." : "Select a customer first." }}
					</span>
				</div>
			</n-upload-dragger>
		</n-upload>

		<n-spin v-if="uploading" show class="self-center" />

		<n-divider class="text-secondary text-xs">or collect a file from an endpoint</n-divider>

		<div class="flex flex-col gap-2">
			<n-select
				v-model:value="selectedClientId"
				:options="agentOptions"
				:loading="agentsLoading"
				:disabled="!customerCode"
				filterable
				clearable
				:placeholder="customerCode ? 'Select an endpoint' : 'Select a customer first'"
				:render-label="renderAgentLabel"
			>
				<template #action>
					<div class="flex items-center justify-between">
						<span class="text-secondary text-xs">
							{{ customerCode ? `${agents.length} endpoint(s) for this customer` : "no customer selected" }}
						</span>
						<n-button text size="tiny" :loading="agentsLoading" :disabled="!customerCode" @click="loadAgents()">
							<template #icon><Icon :name="RefreshIcon" :size="14" /></template>
							Refresh
						</n-button>
					</div>
				</template>
			</n-select>

			<div class="flex gap-2">
				<n-input
					v-model:value="targetPath"
					placeholder="File path or glob (e.g. /tmp/sample, C:\Users\x\*.exe)"
					clearable
					class="grow"
					@keyup.enter="findFiles()"
				>
					<template #prefix><Icon :name="FileIcon" :size="16" /></template>
				</n-input>
				<n-button
					type="primary"
					ghost
					:disabled="!customerCode || !selectedClientId || !targetPath || finding"
					:loading="finding"
					@click="findFiles()"
				>
					<template #icon><Icon :name="SearchIcon" :size="16" /></template>
					Find files
				</n-button>
			</div>

			<!-- Match picker -->
			<div v-if="searched" class="border-default flex flex-col gap-2 rounded-lg border p-3">
				<template v-if="matches.length">
					<div class="flex items-center justify-between">
						<span class="text-sm font-medium">
							{{ matches.length }} file{{ matches.length > 1 ? "s" : "" }} matched — pick what to analyze
						</span>
						<n-button text size="tiny" @click="toggleAll()">
							{{ allSelected ? "Clear" : "Select all" }}
						</n-button>
					</div>
					<n-checkbox-group v-model:value="selectedPaths">
						<div class="flex flex-col gap-1">
							<n-checkbox v-for="m in matches" :key="m.path" :value="m.path">
								<div class="flex items-baseline gap-2">
									<span class="font-medium">{{ m.name }}</span>
									<span class="text-secondary text-xs">{{ fmtBytes(m.size) }}</span>
									<span class="text-secondary font-mono text-xs">{{ m.sha256.slice(0, 12) }}</span>
									<span class="text-secondary truncate text-xs opacity-70">{{ m.path }}</span>
								</div>
							</n-checkbox>
						</div>
					</n-checkbox-group>
					<n-button
						type="primary"
						:disabled="!selectedPaths.length || submitting"
						:loading="submitting"
						@click="analyzeSelected()"
					>
						Analyze selected ({{ selectedPaths.length }})
					</n-button>
				</template>
				<n-empty v-else size="small" description="No files matched that path on this endpoint." />
			</div>

			<span v-else class="text-secondary text-xs">
				CoPilot lists matching files over Velociraptor (auto-detecting the endpoint OS) without pulling any bytes;
				you pick which to collect and analyze.
			</span>
		</div>

		<n-divider />

		<FileAnalysisHistory :customer-code="customerCode || ''" :refresh-key />
	</div>
</template>

<script setup lang="ts">
import type { SelectOption } from "naive-ui"
import type { VNodeChild } from "vue"
import type { ApiError } from "@/types/common"
import type { Customer } from "@/types/customers"
import type { FileAnalysisAgent, FileAnalysisMatch } from "@/types/file-analysis"
import {
	NButton,
	NCheckbox,
	NCheckboxGroup,
	NDivider,
	NEmpty,
	NInput,
	NRadioButton,
	NRadioGroup,
	NSelect,
	NSpin,
	NSwitch,
	NUpload,
	NUploadDragger,
	useMessage
} from "naive-ui"
import { computed, h, onMounted, ref, watch } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import FileAnalysisHistory from "@/components/fileAnalysis/FileAnalysisHistory.vue"
import { getApiErrorMessage } from "@/utils"

const router = useRouter()
const message = useMessage()

const UploadIcon = "carbon:cloud-upload"
const FileIcon = "carbon:document"
const RefreshIcon = "carbon:renew"
const SearchIcon = "carbon:search"
const LS_CUSTOMER = "fileAnalysis.customerCode"

const customerCode = ref<string | null>(null)
const customers = ref<Customer[]>([])
const customersLoading = ref(false)
const uploading = ref(false)
const submitting = ref(false)
const refreshKey = ref(0)

// Pre-analysis phase selection (Tier-1 static always runs).
const sandbox = ref(true)
const vtMode = ref<"off" | "lookup" | "upload">("lookup")

// Endpoint (host_path) collection
const agents = ref<FileAnalysisAgent[]>([])
const agentsLoading = ref(false)
const selectedClientId = ref<string | null>(null)
const targetPath = ref("")

// Match picker
const finding = ref(false)
const searched = ref(false)
const matches = ref<FileAnalysisMatch[]>([])
const selectedPaths = ref<string[]>([])

const customerOptions = computed<SelectOption[]>(() =>
	customers.value.map(c => ({
		label: c.customer_name,
		value: c.customer_code,
		customer: c
	}))
)

const agentOptions = computed<SelectOption[]>(() =>
	agents.value.map(a => ({
		label: a.hostname || a.client_id,
		value: a.client_id,
		agent: a
	}))
)

const allSelected = computed(() => matches.value.length > 0 && selectedPaths.value.length === matches.value.length)

// Remember the last-used customer across visits, and re-scope the endpoint list:
// agents are shown per-customer, so changing customer resets the selection.
watch(customerCode, val => {
	if (val) localStorage.setItem(LS_CUSTOMER, val)
	selectedClientId.value = null
	agents.value = []
	searched.value = false
	matches.value = []
	selectedPaths.value = []
	loadAgents()
})

// A new endpoint or path invalidates the previous match list.
watch([selectedClientId, targetPath], () => {
	searched.value = false
	matches.value = []
	selectedPaths.value = []
})

function fmtBytes(n: number): string {
	if (n < 1024) return `${n} B`
	if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
	return `${(n / 1024 / 1024).toFixed(1)} MB`
}

function renderCustomerLabel(option: SelectOption): VNodeChild {
	const c = option.customer as Customer | undefined
	if (!c) return option.label as string
	return h("div", { class: "flex items-center justify-between gap-3 w-full" }, [
		h("span", c.customer_name),
		h("span", { class: "text-secondary text-xs" }, c.customer_code)
	])
}

function renderAgentLabel(option: SelectOption): VNodeChild {
	const agent = option.agent as FileAnalysisAgent | undefined
	if (!agent) return option.label as string
	return h("div", { class: "flex items-center justify-between gap-3 w-full" }, [
		h("span", { class: "flex items-center gap-2" }, [
			h("span", {
				class: "inline-block w-2 h-2 rounded-full",
				style: { background: agent.online ? "#18a058" : "#909399" }
			}),
			h("span", agent.hostname || agent.client_id),
			agent.unassigned
				? h(
						"span",
						{ class: "text-secondary text-xs rounded px-1", style: { border: "1px solid var(--n-border-color)" } },
						"unassigned"
					)
				: null
		]),
		h("span", { class: "text-secondary text-xs" }, agent.os || "unknown")
	])
}

function toggleAll() {
	selectedPaths.value = allSelected.value ? [] : matches.value.map(m => m.path)
}

function loadCustomers() {
	customersLoading.value = true
	Api.customers
		.getCustomers()
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

function loadAgents() {
	if (!customerCode.value) {
		agents.value = []
		return
	}
	agentsLoading.value = true
	Api.fileAnalysis
		.listAgents(customerCode.value)
		.then(res => {
			if (res.data.success) {
				agents.value = res.data.agents || []
			} else {
				message.warning(res.data?.message || "Could not list endpoints.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Could not reach Velociraptor.")
		})
		.finally(() => {
			agentsLoading.value = false
		})
}

function findFiles() {
	if (!customerCode.value || !selectedClientId.value || !targetPath.value) return
	finding.value = true
	Api.fileAnalysis
		.enumerateFiles({
			customer_code: customerCode.value,
			client_id: selectedClientId.value,
			target_path: targetPath.value
		})
		.then(res => {
			matches.value = res.data.matches || []
			searched.value = true
			selectedPaths.value = matches.value.length === 1 ? [matches.value[0].path] : []
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Could not enumerate files.")
		})
		.finally(() => {
			finding.value = false
		})
}

async function analyzeSelected() {
	if (!customerCode.value || !selectedClientId.value || !selectedPaths.value.length) return
	submitting.value = true
	try {
		const results = await Promise.all(
			selectedPaths.value.map(path =>
				Api.fileAnalysis
					.submit({
						source: "host_path",
						customer_code: customerCode.value as string,
						client_id: selectedClientId.value as string,
						target_path: path,
						tiers: sandbox.value ? ["static", "dynamic"] : ["static"],
						reputation_mode: vtMode.value
					})
					.then(r => (r.data?.success ? r.data.job_id : null))
					.catch(() => null)
			)
		)
		const jobIds = results.filter((id): id is string => Boolean(id))
		if (!jobIds.length) {
			message.error("No analyses could be started.")
			return
		}
		refreshKey.value++
		if (jobIds.length < selectedPaths.value.length) {
			message.warning(`Started ${jobIds.length} of ${selectedPaths.value.length}.`)
		} else if (jobIds.length > 1) {
			message.success(`Started ${jobIds.length} analyses.`)
		}
		// Carry the whole batch so the result view can show all of them in a sidebar.
		const query = jobIds.length > 1 ? { batch: jobIds.join(",") } : undefined
		router.push({ name: "FileAnalysis", params: { jobId: jobIds[0] }, query })
	} finally {
		submitting.value = false
	}
}

function handleUpload({ file, onFinish, onError }: import("naive-ui").UploadCustomRequestOptions) {
	if (!file.file || !customerCode.value) {
		onError()
		return
	}
	uploading.value = true
	Api.fileAnalysis
		.upload(file.file, customerCode.value, { sandbox: sandbox.value, reputationMode: vtMode.value })
		.then(res => {
			if (res.data.success && res.data.job_id) {
				onFinish()
				router.push({ name: "FileAnalysis", params: { jobId: res.data.job_id } })
			} else {
				message.warning(res.data?.message || "Upload failed.")
				onError()
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Upload failed.")
			onError()
		})
		.finally(() => {
			uploading.value = false
		})
}

onMounted(() => {
	// Agents load per-customer via the customerCode watcher (incl. the restored one).
	loadCustomers()
})
</script>
