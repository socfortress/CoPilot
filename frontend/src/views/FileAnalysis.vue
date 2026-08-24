<template>
	<div class="page">
		<!-- No job selected → submit / upload panel -->
		<FileAnalysisSubmit v-if="!jobId" />

		<div v-else class="flex flex-col gap-4 md:flex-row md:items-start">
			<!-- Batch sidebar — when several files were analyzed together -->
			<FileAnalysisBatchList
				v-if="batchIds.length > 1"
				:job-ids="batchIds"
				:active-job-id="jobId"
				class="w-full md:w-64 md:shrink-0"
			/>

			<div class="flex min-w-0 grow flex-col gap-4">
				<!-- Header -->
				<div class="flex flex-wrap items-center gap-3">
					<Icon :name="FileIcon" :size="20" />
					<span class="text-lg font-semibold">{{ job?.filename || "File analysis" }}</span>
					<n-tag v-if="vtLabel" :type="vtType" size="small" round :bordered="false">
						<template #icon><Icon :name="VtIcon" :size="14" /></template>
						{{ vtLabel }}
					</n-tag>
					<n-spin v-if="stillRunning || vtPending" :size="16" />
					<div class="grow" />
					<n-tag v-if="job?.customer_code" size="small" round :bordered="false">
						<template #icon><Icon :name="CustomerIcon" :size="14" /></template>
						{{ job.customer_code }}
					</n-tag>
					<code v-if="shaShort" class="text-secondary text-xs">{{ shaShort }}</code>
				</div>

				<!-- Dev-mode (unhardened) banner -->
				<n-alert v-if="job && job.hardened === false" type="warning" :bordered="false" class="text-sm">
					This result came from the dev-only in-process inspector — <b>no container isolation</b>. Not for production
					triage.
				</n-alert>

				<n-alert v-if="job?.status === 'failed'" type="error" :bordered="false" class="text-sm">
					Analysis failed. A file that crashes the inspector is itself worth a look.
				</n-alert>

				<!-- VirusTotal reputation -->
				<ReputationCard :reputation="result?.reputation" :loading="stillRunning" />

				<!-- Always-populated summary -->
				<FileAnalysisOverview
					:result="result?.inspector"
					:job
					:reputation-pending="vtPending"
					:verdict-reason="result?.verdict_reason"
				/>

				<!-- Tabs (empty ones are hidden; we land on the first with content) -->
				<n-tabs v-model:value="activeTab" type="line" animated @update:value="tabPinnedByUser = true">
					<n-tab-pane v-if="hasPreviews" name="preview" tab="Preview" display-directive="show:lazy">
						<PreviewTab :job-id :preview-names="result?.preview_urls || []" :loading="loadingResult" />
					</n-tab-pane>
					<n-tab-pane v-if="hasContent" name="content" tab="Content" display-directive="show:lazy">
						<ContentTab :result="result?.inspector" :loading="loadingResult" />
					</n-tab-pane>
					<n-tab-pane v-if="hasIocs" name="iocs" tab="IOCs" display-directive="show:lazy">
						<IocsTab :iocs="result?.inspector?.iocs" />
					</n-tab-pane>
					<n-tab-pane v-if="hasVtIntel" name="virustotal" tab="VirusTotal" display-directive="show:lazy">
						<VirusTotalTab :reputation="result?.reputation" :loading="stillRunning" />
					</n-tab-pane>
					<n-tab-pane name="metadata" tab="Metadata" display-directive="show:lazy">
						<MetadataTab :result="result?.inspector" />
					</n-tab-pane>

					<!-- Detonation tabs only when the backend reports sandbox enabled -->
					<template v-if="hasSandbox">
						<n-tab-pane name="detonation" tab="Detonation" display-directive="show:lazy">
							<DetonationTab
								:sandbox="result?.sandbox"
								:loading="loadingResult"
								:dynamic-status="job?.dynamic_status"
								:job-id
							/>
						</n-tab-pane>
						<n-tab-pane name="network" tab="Network" display-directive="show:lazy">
							<NetworkTab :sandbox="result?.sandbox" :loading="loadingResult" />
						</n-tab-pane>
					</template>
				</n-tabs>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { FileAnalysisJob, FileAnalysisResult } from "@/types/file-analysis"
import { NAlert, NSpin, NTabPane, NTabs, NTag, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, onBeforeUnmount, ref, watch } from "vue"
import { useRoute } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { resolveActiveTab } from "@/components/fileAnalysis/fileAnalysis.helpers"
import FileAnalysisBatchList from "@/components/fileAnalysis/FileAnalysisBatchList.vue"
import FileAnalysisOverview from "@/components/fileAnalysis/FileAnalysisOverview.vue"
import FileAnalysisSubmit from "@/components/fileAnalysis/FileAnalysisSubmit.vue"
import ReputationCard from "@/components/fileAnalysis/ReputationCard.vue"
import { getApiErrorMessage } from "@/utils"

const PreviewTab = defineAsyncComponent(() => import("@/components/fileAnalysis/tabs/PreviewTab.vue"))
const ContentTab = defineAsyncComponent(() => import("@/components/fileAnalysis/tabs/ContentTab.vue"))
const IocsTab = defineAsyncComponent(() => import("@/components/fileAnalysis/tabs/IocsTab.vue"))
const MetadataTab = defineAsyncComponent(() => import("@/components/fileAnalysis/tabs/MetadataTab.vue"))
const DetonationTab = defineAsyncComponent(() => import("@/components/fileAnalysis/tabs/DetonationTab.vue"))
const VirusTotalTab = defineAsyncComponent(() => import("@/components/fileAnalysis/tabs/VirusTotalTab.vue"))
const NetworkTab = defineAsyncComponent(() => import("@/components/fileAnalysis/tabs/NetworkTab.vue"))

const route = useRoute()
const message = useMessage()

const FileIcon = "carbon:document-security"
const CustomerIcon = "carbon:user"
const VtIcon = "carbon:radar"
const POLL_MS = 3000
const MAX_POLLS = 120 // ~6 min ceiling so a slow VT scan doesn't poll forever

const jobId = computed(() => (route.params.jobId as string) || "")
// A batch of files analyzed together (via ?batch=id1,id2,…) shows a sidebar to flip
// between them, so analyzing N files doesn't hide N-1 of the results.
const batchIds = computed(() =>
	((route.query.batch as string) || "")
		.split(",")
		.map(s => s.trim())
		.filter(Boolean)
)
const activeTab = ref<string>("metadata")
// Set the moment the analyst clicks a tab: from then on the view stops following
// the content and stays where they put it.
const tabPinnedByUser = ref(false)
const job = ref<FileAnalysisJob | null>(null)
const result = ref<FileAnalysisResult | null>(null)
const loadingResult = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null
let pollCount = 0

const shaShort = computed(() => (job.value?.sha256 || result.value?.inspector?.sha256 || "").slice(0, 16))

// Header indicator is SOLELY the VirusTotal result — the multi-engine hit ratio.
const reputation = computed(() => result.value?.reputation || null)
const vtPending = computed(() => {
	const r = reputation.value
	return !!(r && r.submitted && !r.found)
})
const vtLabel = computed<string | null>(() => {
	const r = reputation.value
	if (!r || r.skipped) return null
	if (r.found) return `VirusTotal ${r.malicious ?? 0}/${r.total ?? "?"}`
	if (r.submitted) return "VirusTotal scanning…"
	return "VirusTotal: not seen"
})
const vtType = computed<"error" | "warning" | "success" | "default">(() => {
	const r = reputation.value
	if (!r || !r.found) return "default"
	const m = r.malicious ?? 0
	if (m >= 5) return "error"
	if (m >= 1 || (r.suspicious ?? 0) >= 1) return "warning"
	return "success"
})

// Which detail tabs actually have content — empty ones are hidden and we never
// land on them (the old default was always "Preview", blank for non-document files).
const hasPreviews = computed(() => (result.value?.preview_urls?.length ?? 0) > 0)
const hasContent = computed(() => {
	const c = result.value?.inspector?.content
	if (!c) return false
	return Boolean(
		c.raw ||
			c.macros ||
			c.javascript ||
			c.text ||
			c.arguments ||
			c.target ||
			c.capabilities?.length ||
			c.strings?.length ||
			c.sections?.length
	)
})
const hasIocs = computed(() => {
	const i = result.value?.inspector?.iocs
	return Boolean(i && ((i.urls?.length ?? 0) + (i.ips?.length ?? 0) + (i.domains?.length ?? 0) > 0))
})

// The VirusTotal tab appears only when VT knows the file AND deep intel came back.
const hasVtIntel = computed(() => Boolean(result.value?.reputation?.found && result.value?.reputation?.intel))

// Detonation/Network are gated on the backend reporting a sandbox, not on a report
// existing — an in-flight detonation must still be reachable.
const hasSandbox = computed(() => job.value?.sandbox_enabled === true)

// Land on the first tab that has something; Metadata is the always-present fallback.
// Availability changes mid-view as polling fills the result in, so resolveActiveTab
// keeps the analyst on their current tab whenever it still exists.
watch(
	[hasPreviews, hasContent, hasIocs, hasVtIntel, hasSandbox],
	() => {
		activeTab.value = resolveActiveTab(
			activeTab.value,
			{
				previews: hasPreviews.value,
				content: hasContent.value,
				iocs: hasIocs.value,
				vtIntel: hasVtIntel.value,
				sandbox: hasSandbox.value
			},
			tabPinnedByUser.value
		)
	},
	{ immediate: true }
)

const stillRunning = computed(() => {
	const s = job.value?.status
	if (!s) return true
	if (["pending", "queued", "running"].includes(s)) return true
	// Sandbox may still be detonating after the static tier is done.
	return job.value?.sandbox_enabled === true && job.value?.dynamic_status !== undefined && !["done", "failed"].includes(job.value.dynamic_status)
})

function stopPolling() {
	if (pollTimer) {
		clearInterval(pollTimer)
		pollTimer = null
	}
}

function fetchJob() {
	if (!jobId.value) return
	Api.fileAnalysis
		.getJob(jobId.value)
		.then(res => {
			if (res.data.success) {
				job.value = res.data.job
				// Only pull the result once Tier 1 has SAVED it (static_status done/…).
				// While it's still "running" the result 404s, so don't ask yet.
				if (["done", "failed"].includes(res.data.job.static_status)) {
					fetchResult()
				}
				pollCount += 1
				// Keep polling while the job runs, OR while a detached VT scan is
				// still pending (bounded) so its result gets picked up.
				const keepGoing = stillRunning.value || (vtPending.value && pollCount < MAX_POLLS)
				if (!keepGoing) stopPolling()
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Failed to load job status.")
			stopPolling()
		})
}

function fetchResult() {
	if (!jobId.value || loadingResult.value) return
	loadingResult.value = true
	Api.fileAnalysis
		.getResult(jobId.value)
		.then(res => {
			if (res.data.success) result.value = res.data.result
		})
		.catch(() => {
			/* result may not be ready yet; polling will retry */
		})
		.finally(() => {
			loadingResult.value = false
		})
}

function start() {
	stopPolling()
	job.value = null
	result.value = null
	pollCount = 0
	tabPinnedByUser.value = false
	if (!jobId.value) return
	fetchJob()
	pollTimer = setInterval(fetchJob, POLL_MS)
}

watch(jobId, start, { immediate: true })
onBeforeUnmount(stopPolling)
</script>
