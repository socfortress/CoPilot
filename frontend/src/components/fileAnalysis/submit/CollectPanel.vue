<template>
	<div class="flex flex-col gap-3">
		<p class="text-secondary text-sm">
			CoPilot lists matching files over Velociraptor (auto-detecting the endpoint OS) without pulling any bytes;
			you pick which to collect and analyze.
		</p>

		<!-- Loud on purpose: a mocked endpoint list looks exactly like a real one, and
		     mistaking one for the other during review is the whole risk here. -->
		<n-alert v-if="USE_MOCK_COLLECT" type="warning" :bordered="false" class="text-sm">
			<template #header>Mock data — no endpoint is being contacted</template>
			Endpoints and file matches are fabricated locally so the selection flow can be exercised without a live
			Velociraptor. Path keywords drive the outcome:
			<b>one</b>
			= single match,
			<b>empty</b>
			= no matches,
			<b>fail</b>
			= error. A backslash or drive letter yields Windows-style files.
		</n-alert>

		<n-select
			v-model:value="selectedClientId"
			:options="agentOptions"
			:loading="agentsLoading"
			:disabled="!customerCode || finding"
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
				:disabled="!customerCode || !selectedClientId || finding"
				class="grow"
				@keyup.enter="findFiles()"
			>
				<template #prefix><Icon :name="FileIcon" :size="16" /></template>
			</n-input>
			<n-button
				type="primary"
				ghost
				:disabled="!customerCode || !selectedClientId || !targetPath || finding || agentsLoading"
				:loading="finding"
				@click="findFiles()"
			>
				<template #icon><Icon :name="SearchIcon" :size="16" /></template>
				Find files
			</n-button>
		</div>

		<!-- Enumeration failure stays on screen next to the input that caused it: a
		     toast disappears before the analyst has finished re-reading their path,
		     and a wrong glob or an offline endpoint is corrected right here. -->
		<n-alert v-if="findError" type="error" :bordered="false" closable @close="findError = null">
			<template #header>Could not list files on that endpoint</template>
			<span class="text-sm">{{ findError }}</span>
		</n-alert>

		<!-- Match picker -->
		<div v-if="searched" class="border-default flex flex-col overflow-hidden rounded-lg border">
			<template v-if="matches.length">
				<div
					class="border-default bg-secondary flex flex-wrap items-center justify-between gap-2 border-b px-3 py-2"
				>
					<span class="text-secondary font-mono text-xs">
						{{ matches.length }} match{{ matches.length > 1 ? "es" : "" }}
						<template v-if="selectedPaths.length">
							· {{ selectedPaths.length }} selected · {{ fmtBytes(selectedSize) }}
						</template>
					</span>
					<n-button text size="tiny" @click="toggleAll()">
						{{ allSelected ? "Clear" : "Select all" }}
					</n-button>
				</div>

				<n-checkbox-group v-model:value="selectedPaths" class="flex flex-col">
					<n-checkbox
						v-for="m in matches"
						:key="m.path"
						:value="m.path"
						class="match-row"
						:class="{ 'is-selected': selectedPaths.includes(m.path) }"
					>
						<div class="flex min-w-0 flex-col gap-0.5">
							<!-- Name and the technical columns share a wrapping row, so the size
							     and hash drop under the name instead of squeezing it. -->
							<div class="flex flex-wrap items-center gap-x-3 gap-y-1">
								<Icon :name="iconForFile(m.name)" :size="15" class="text-secondary shrink-0" />
								<span class="text-default min-w-0 grow basis-40 truncate text-sm font-medium">
									{{ m.name }}
								</span>
								<span class="text-tertiary shrink-0 font-mono text-xs tabular-nums">
									{{ fmtBytes(m.size) }}
								</span>
								<span class="text-tertiary shrink-0 font-mono text-xs">
									{{ m.sha256.slice(0, 12) }}
								</span>
							</div>
							<!-- Full path on its own line: it is the longest field and the one that
							     disambiguates two files sharing a name. -->
							<span class="text-tertiary text-2xs truncate font-mono" :title="m.path">{{ m.path }}</span>
						</div>
					</n-checkbox>
				</n-checkbox-group>

				<div class="border-default border-t p-3">
					<n-button
						type="primary"
						block
						:disabled="!selectedPaths.length || submitting"
						:loading="submitting"
						@click="analyzeSelected()"
					>
						Analyze selected ({{ selectedPaths.length }})
					</n-button>
				</div>
			</template>

			<n-empty v-else size="small" description="No files matched that path on this endpoint." class="py-6" />
		</div>
	</div>
</template>

<script setup lang="ts">
import type { SelectOption } from "naive-ui"
import type { VNodeChild } from "vue"
import type { ApiError } from "@/types/common"
import type { FileAnalysisAgent, FileAnalysisMatch, ReputationMode } from "@/types/file-analysis"
import { NAlert, NButton, NCheckbox, NCheckboxGroup, NEmpty, NInput, NSelect, useMessage } from "naive-ui"
import { computed, h, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { mockEnumerate, mockListAgents, mockSubmit, USE_MOCK_COLLECT } from "@/components/fileAnalysis/submit/mock"
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
const findError = ref<string | null>(null)
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

const selectedSize = computed(() =>
	matches.value.filter(m => selectedPaths.value.includes(m.path)).reduce((sum, m) => sum + m.size, 0)
)

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
	findError.value = null
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

// Extension → icon. Scanning collected files is mostly asking "which of these is
// executable content", so the families that answer that get their own glyph and
// everything else falls back to a plain document.
const FILE_ICONS: Record<string, string> = {
	exe: "carbon:executable-program",
	dll: "carbon:executable-program",
	sys: "carbon:executable-program",
	elf: "carbon:executable-program",
	so: "carbon:executable-program",
	bin: "carbon:executable-program",
	ps1: "carbon:script",
	sh: "carbon:script",
	bat: "carbon:script",
	cmd: "carbon:script",
	py: "carbon:script",
	js: "carbon:script",
	vbs: "carbon:script",
	hta: "carbon:script",
	zip: "carbon:archive",
	"7z": "carbon:archive",
	rar: "carbon:archive",
	gz: "carbon:archive",
	tar: "carbon:archive",
	cab: "carbon:archive",
	pdf: "carbon:document-pdf",
	png: "carbon:image",
	jpg: "carbon:image",
	jpeg: "carbon:image",
	gif: "carbon:image",
	svg: "carbon:image",
	bmp: "carbon:image",
	txt: "carbon:document-blank",
	log: "carbon:document-blank",
	csv: "carbon:document-blank",
	json: "carbon:code",
	xml: "carbon:code"
}

function iconForFile(name: string): string {
	const ext = name.split(".").pop()?.toLowerCase() || ""
	return FILE_ICONS[ext] || "carbon:document"
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

	if (USE_MOCK_COLLECT) {
		mockListAgents()
			.then(list => (agents.value = list))
			.finally(() => (agentsLoading.value = false))
		return
	}

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
	findError.value = null

	if (USE_MOCK_COLLECT) {
		mockEnumerate(targetPath.value)
			.then(list => {
				matches.value = list
				searched.value = true
				selectedPaths.value = list.length === 1 ? [list[0].path] : []
			})
			.catch(err => {
				searched.value = false
				findError.value = (err as Error).message
			})
			.finally(() => (finding.value = false))
		return
	}

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
			searched.value = false
			findError.value = getApiErrorMessage(err as ApiError) || "Could not enumerate files."
		})
		.finally(() => {
			finding.value = false
		})
}

async function analyzeSelected() {
	if (!props.customerCode || !selectedClientId.value || !selectedPaths.value.length) return
	submitting.value = true
	try {
		// Mocked submission stops here on purpose: emitting would navigate to a job
		// id the backend has never heard of, and the result view would poll a 404.
		// What is worth checking at this point is the payload, so it is reported
		// instead. Swap the message for `emit("started", ids)` to exercise routing.
		if (USE_MOCK_COLLECT) {
			const ids = await mockSubmit(selectedPaths.value)
			const tiers = props.sandbox ? "static + dynamic" : "static only"
			message.info(
				`Mock: would start ${ids.length} analysis/analyses — tiers: ${tiers}, VirusTotal: ${props.vtMode}.`
			)
			return
		}

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

<style scoped lang="scss">
.match-row {
	display: flex;
	align-items: flex-start;
	width: 100%;
	padding: 0.5rem 0.75rem;
	// Transparent rather than absent, so selecting a row does not shift its text.
	box-shadow: inset 3px 0 0 0 transparent;
	transition:
		box-shadow 0.15s ease,
		background-color 0.15s ease;

	// Naive lays a checkbox out inline; the label has to become a full-width block
	// for the name to truncate instead of pushing the technical columns off-row.
	:deep(.n-checkbox__label) {
		width: 100%;
		min-width: 0;
		padding-left: 0.5rem;
	}

	& + .match-row {
		border-top: 1px solid var(--border-color);
	}

	&:hover {
		background-color: var(--hover-005-color);
	}

	// Same accent language as the analysis-phase rows: a left rule means
	// "this is in the plan".
	&.is-selected {
		box-shadow: inset 3px 0 0 0 var(--primary-color);
		background-color: color-mix(in srgb, var(--primary-color) 4%, transparent);
	}
}
</style>
