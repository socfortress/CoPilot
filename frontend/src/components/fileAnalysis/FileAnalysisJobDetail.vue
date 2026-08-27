<template>
	<!-- Nothing at all is known yet: show the page's shape rather than an empty one.
	     The whole view then appears in a single step instead of assembling itself
	     block by block in front of the analyst. -->
	<FileAnalysisDetailSkeleton v-if="initialLoading" />

	<!-- The first fetch failed: say so here. Left to the toast alone, the page would
	     sit on its skeleton for good, which is the very stall this state prevents. -->
	<n-alert v-else-if="loadError" type="error" :bordered="false" class="text-sm">
		{{ loadError }}
	</n-alert>

	<div v-else class="flex flex-col gap-4">
		<FileAnalysisDetailHeader
			:job
			:result
			:batch-count="batchIds.length"
			:running="stillRunning || vtPending"
			@open-batch="showBatch = true"
		/>

		<!-- The one place the unhardened state is stated, and it carries the
		     consequence rather than just the label. -->
		<n-alert v-if="job && job.hardened === false" type="warning" :bordered="false" class="text-sm">
			This result came from the dev-only in-process inspector —
			<b>no container isolation</b>
			. Not for production triage.
		</n-alert>

		<n-alert v-if="job?.status === 'failed'" type="error" :bordered="false" class="text-sm">
			Analysis failed. A file that crashes the inspector is itself worth a look.
		</n-alert>

		<!-- The job is known but its result is not readable yet. Naming the stage is
		     what makes the wait read as expected rather than as a stall — the tab
		     strip stays out until it can be drawn complete. -->
		<FileAnalysisProgress v-if="awaitingResult" :job :reputation-pending="vtPending" />

		<template v-else>
			<FileAnalysisOverview
				:result="result?.inspector"
				:reputation="result?.reputation"
				:reputation-pending="vtPending"
				:verdict-reason="result?.verdict_reason"
			/>

			<!-- A later tier can still be running once the static result is readable;
			     say so under the content instead of leaving a half-filled page. -->
			<FileAnalysisProgress v-if="stillRunning" :job :reputation-pending="vtPending" />

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
		</template>

		<!-- Batch moved out of the layout: as a sidebar it squeezed the content column
		     on every screen, including the common case of a single-file analysis. -->
		<n-drawer v-model:show="showBatch" :width="640" class="max-w-[90vw]!" placement="right">
			<n-drawer-content title="Batch" closable :native-scrollbar="false">
				<FileAnalysisBatchList
					v-if="batchIds.length > 1"
					:job-ids="batchIds"
					:active-job-id="jobId"
					@select="showBatch = false"
				/>
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { FileAnalysisJob, FileAnalysisResult } from "@/types/file-analysis"
import { NAlert, NDrawer, NDrawerContent, NTabPane, NTabs, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, onBeforeUnmount, ref, watch } from "vue"
import Api from "@/api"
import { resolveActiveTab } from "@/components/fileAnalysis/fileAnalysis.helpers"
import FileAnalysisBatchList from "@/components/fileAnalysis/FileAnalysisBatchList.vue"
import FileAnalysisDetailHeader from "@/components/fileAnalysis/FileAnalysisDetailHeader.vue"
import FileAnalysisDetailSkeleton from "@/components/fileAnalysis/FileAnalysisDetailSkeleton.vue"
import FileAnalysisOverview from "@/components/fileAnalysis/FileAnalysisOverview.vue"
import FileAnalysisProgress from "@/components/fileAnalysis/FileAnalysisProgress.vue"
import {
	MOCK_JOB_ID,
	MOCK_LATENCY_MS,
	mockJob,
	mockResult,
	USE_MOCK_ANALYSIS
} from "@/components/fileAnalysis/mock-analysis"
import TabLoading from "@/components/fileAnalysis/tabs/TabLoading.vue"
import { getApiErrorMessage } from "@/utils"

// Route state arrives as props: the view owns the URL, this component owns one
// job's polling and rendering. That keeps it mountable anywhere a job id is known
// (a drawer, a case page) without inventing a route to get there.
const props = withDefaults(defineProps<{ jobId: string; batchIds?: string[] }>(), { batchIds: () => [] })

// Each panel is its own chunk. The fallback keeps a switch to a not-yet-downloaded
// tab from showing an empty pane; the delay keeps it from flashing when the chunk
// is already cached, which is the common case after the first visit.
function tabChunk(loader: () => Promise<unknown>) {
	return defineAsyncComponent({
		loader: loader as never,
		loadingComponent: TabLoading,
		delay: 120
	})
}

const PreviewTab = tabChunk(() => import("@/components/fileAnalysis/tabs/PreviewTab.vue"))
const ContentTab = tabChunk(() => import("@/components/fileAnalysis/tabs/ContentTab.vue"))
const IocsTab = tabChunk(() => import("@/components/fileAnalysis/tabs/IocsTab.vue"))
const MetadataTab = tabChunk(() => import("@/components/fileAnalysis/tabs/MetadataTab.vue"))
const DetonationTab = tabChunk(() => import("@/components/fileAnalysis/tabs/DetonationTab.vue"))
const VirusTotalTab = tabChunk(() => import("@/components/fileAnalysis/tabs/VirusTotalTab.vue"))
const NetworkTab = tabChunk(() => import("@/components/fileAnalysis/tabs/NetworkTab.vue"))

const message = useMessage()

const POLL_MS = 3000
const MAX_POLLS = 120 // ~6 min ceiling so a slow VT scan doesn't poll forever

const showBatch = ref(false)
const activeTab = ref<string>("metadata")
// Set the moment the analyst clicks a tab: from then on the view stops following
// the content and stays where they put it.
const tabPinnedByUser = ref(false)
const job = ref<FileAnalysisJob | null>(null)
const result = ref<FileAnalysisResult | null>(null)
const loadingResult = ref(false)
const loadError = ref("")
let pollTimer: ReturnType<typeof setInterval> | null = null
let pollCount = 0

// Three phases, so the page never renders half-built: nothing known yet (shape
// only), the job known but its result not readable (named stages), everything
// readable (the real view, drawn once and complete).
const initialLoading = computed(() => !job.value && !loadError.value)
const awaitingResult = computed(() => !result.value && job.value?.status !== "failed")

// Header indicator is SOLELY the VirusTotal result — the multi-engine hit ratio.
const reputation = computed(() => result.value?.reputation || null)
const vtPending = computed(() => {
	const r = reputation.value
	return !!(r && r.submitted && !r.found)
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
	return Boolean(i && (i.urls?.length ?? 0) + (i.ips?.length ?? 0) + (i.domains?.length ?? 0) > 0)
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
	return (
		job.value?.sandbox_enabled === true &&
		job.value?.dynamic_status !== undefined &&
		!["done", "failed"].includes(job.value.dynamic_status)
	)
})

function stopPolling() {
	if (pollTimer) {
		clearInterval(pollTimer)
		pollTimer = null
	}
}

function fetchJob() {
	if (!props.jobId) return
	Api.fileAnalysis
		.getJob(props.jobId)
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
	if (!props.jobId || loadingResult.value) return
	loadingResult.value = true
	Api.fileAnalysis
		.getResult(props.jobId)
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
	loadError.value = ""
	pollCount = 0
	tabPinnedByUser.value = false
	if (!props.jobId) return

	// Dev fixture: one job id renders a fully-populated analysis so every panel on
	// this page can be reviewed at once. No real sample fills them all.
	if (USE_MOCK_ANALYSIS && props.jobId === MOCK_JOB_ID) {
		// Resolved after a beat rather than synchronously: the fixture exists to review
		// this page, and a mock that lands instantly is the one state the real page
		// never has — the loading path would go unreviewed.
		const id = props.jobId
		setTimeout(() => {
			if (props.jobId !== id) return
			job.value = mockJob()
			result.value = mockResult()
		}, MOCK_LATENCY_MS)
		return
	}

	fetchJob()
	pollTimer = setInterval(fetchJob, POLL_MS)
}

// Switching between jobs in a batch reuses this component instance, so the restart
// hangs off the prop rather than off mount.
watch(() => props.jobId, start, { immediate: true })
onBeforeUnmount(stopPolling)
</script>
