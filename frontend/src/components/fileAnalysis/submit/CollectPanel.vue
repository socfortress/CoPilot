<template>
	<div class="flex flex-col gap-3">
		<p class="text-secondary text-sm">
			CoPilot lists matching files over Velociraptor (auto-detecting the endpoint OS) without pulling any bytes; you
			pick which to collect and analyze.
		</p>

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
	</div>
</template>

<script setup lang="ts">
import type { SelectOption } from "naive-ui"
import type { VNodeChild } from "vue"
import type { ApiError } from "@/types/common"
import type { FileAnalysisAgent, FileAnalysisMatch, ReputationMode } from "@/types/file-analysis"
import { NButton, NCheckbox, NCheckboxGroup, NEmpty, NInput, NSelect, useMessage } from "naive-ui"
import { computed, h, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{ customerCode: string | null; sandbox: boolean; vtMode: ReputationMode }>()

// The panel starts the jobs; the shell owns where the analyst goes next, so both
// submission paths land on the result view the same way.
const emit = defineEmits<{ (e: "started", jobIds: string[]): void }>()

const message = useMessage()

const FileIcon = "carbon:document"
const RefreshIcon = "carbon:renew"
const SearchIcon = "carbon:search"

const agents = ref<FileAnalysisAgent[]>([])
const agentsLoading = ref(false)
const selectedClientId = ref<string | null>(null)
const targetPath = ref("")

const finding = ref(false)
const searched = ref(false)
const submitting = ref(false)
const matches = ref<FileAnalysisMatch[]>([])
const selectedPaths = ref<string[]>([])

const agentOptions = computed<SelectOption[]>(() =>
	agents.value.map(a => ({
		label: a.hostname || a.client_id,
		value: a.client_id,
		agent: a
	}))
)

const allSelected = computed(() => matches.value.length > 0 && selectedPaths.value.length === matches.value.length)

// Agents are listed per-customer, so a customer change invalidates the endpoint,
// the match list and the selection alike.
watch(
	() => props.customerCode,
	() => {
		selectedClientId.value = null
		agents.value = []
		clearMatches()
		loadAgents()
	},
	{ immediate: true }
)

// A different endpoint or path invalidates the previous match list too.
watch([selectedClientId, targetPath], clearMatches)

function clearMatches() {
	searched.value = false
	matches.value = []
	selectedPaths.value = []
}

function fmtBytes(n: number): string {
	if (n < 1024) return `${n} B`
	if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
	return `${(n / 1024 / 1024).toFixed(1)} MB`
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
						{
							class: "text-secondary text-xs rounded px-1",
							style: { border: "1px solid var(--n-border-color)" }
						},
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

function loadAgents() {
	if (!props.customerCode) {
		agents.value = []
		return
	}
	agentsLoading.value = true
	Api.fileAnalysis
		.listAgents(props.customerCode)
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
	if (!props.customerCode || !selectedClientId.value || !targetPath.value) return
	finding.value = true
	Api.fileAnalysis
		.enumerateFiles({
			customer_code: props.customerCode,
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
	if (!props.customerCode || !selectedClientId.value || !selectedPaths.value.length) return
	submitting.value = true
	try {
		// One submit per file: a single unreadable path must not sink the batch.
		const results = await Promise.all(
			selectedPaths.value.map(path =>
				Api.fileAnalysis
					.submit({
						source: "host_path",
						customer_code: props.customerCode as string,
						client_id: selectedClientId.value as string,
						target_path: path,
						tiers: props.sandbox ? ["static", "dynamic"] : ["static"],
						reputation_mode: props.vtMode
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
		if (jobIds.length < selectedPaths.value.length) {
			message.warning(`Started ${jobIds.length} of ${selectedPaths.value.length}.`)
		} else if (jobIds.length > 1) {
			message.success(`Started ${jobIds.length} analyses.`)
		}
		emit("started", jobIds)
	} finally {
		submitting.value = false
	}
}
</script>
