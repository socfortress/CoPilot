<template>
	<section class="flex flex-col gap-4" data-testid="cloud-scan-view">
		<!-- The scan: its state, when and how it ran, and what can be done with it. -->
		<div class="flex flex-wrap items-center gap-x-3 gap-y-2">
			<h3 class="m-0 text-base font-semibold">Scan #{{ scan.id }}</h3>
			<CloudScanStatusTag :status="scan.status" />
			<span class="text-secondary text-xs">
				<template v-if="scan.started_at">started {{ formatDate(scan.started_at, dFormats.datetime) }}</template>
				<template v-else>queued {{ formatDate(scan.queued_at ?? "", dFormats.datetime) }}</template>
				<template v-if="duration">· took {{ duration }}</template>
				· {{ scan.trigger_type === "schedule" ? "scheduled" : `by ${scan.requested_by ?? "an analyst"}` }}
				<template v-if="scan.prowler_version">· Prowler {{ scan.prowler_version }}</template>
			</span>
			<div class="ml-auto flex flex-wrap gap-2">
				<n-button
					v-for="kind of scan.reports"
					:key="kind"
					size="small"
					secondary
					:loading="downloading === kind"
					:data-testid="`cloud-report-${kind}`"
					@click="download(kind)"
				>
					<template #icon><Icon :name="DownloadIcon" /></template>
					{{ kind === "html" ? "HTML report" : "CSV" }}
				</n-button>
				<n-button v-if="cancellable" size="small" secondary :loading="cancelling" @click="cancel()">Cancel scan</n-button>
				<n-popconfirm v-if="isAdmin && !active" @positive-click="remove()">
					<template #trigger>
						<n-button size="small" secondary type="error" :loading="deleting">Delete scan</n-button>
					</template>
					Delete this scan with its findings and reports?
				</n-popconfirm>
			</div>
		</div>

		<n-alert v-if="scan.status === 'failed'" type="error" :bordered="false" data-testid="cloud-scan-error">
			<div class="flex flex-col gap-1">
				<span>{{ scan.error_message ?? "The scan failed." }}</span>
				<span v-if="scan.prowler_errors.length" class="text-xs opacity-80">
					Prowler raised
					<code>{{ scan.prowler_errors.join(", ") }}</code>
				</span>
			</div>
		</n-alert>
		<n-alert v-else-if="active" type="info" :bordered="false" data-testid="cloud-scan-active">
			{{ activeText }}
		</n-alert>

		<template v-if="scan.status === 'completed'">
			<n-alert v-if="scan.check_errors" type="warning" :bordered="false">
				{{ scan.check_errors }} check{{ scan.check_errors === 1 ? "" : "s" }} logged an error during the scan: a
				permission the credential lacks, usually. Those checks' results may be missing.
			</n-alert>
			<n-alert v-if="scan.findings_pruned" type="info" :bordered="false">
				Retention removed this scan's findings and reports. Its counts and checks remain.
			</n-alert>

			<n-tabs v-model:value="tabModel" type="line" animated>
				<n-tab-pane name="overview" tab="Overview" display-directive="show:lazy">
					<div class="flex flex-col gap-4 pt-2">
						<dl class="bg-border border-default m-0 grid grid-cols-2 gap-px overflow-hidden rounded-lg border md:grid-cols-6">
							<div v-for="tile of tiles" :key="tile.key" class="bg-default flex flex-col gap-1 px-4 py-3" :data-testid="`cloud-scan-tile-${tile.key}`">
								<dt :class="SECTION_LABEL">{{ tile.label }}</dt>
								<dd class="m-0 flex items-baseline gap-2">
									<span class="font-mono text-xl font-semibold tabular-nums" :class="tile.tone">{{ tile.value }}</span>
									<span v-if="tile.hint" class="text-tertiary text-xs">{{ tile.hint }}</span>
								</dd>
							</div>
						</dl>
						<div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
							<section class="border-default bg-default flex flex-col gap-3 rounded-lg border p-4">
								<span :class="SECTION_LABEL">Failing by severity</span>
								<CloudSeverityBars :counts="scan.counts" />
							</section>
							<section class="border-default bg-default flex flex-col gap-3 rounded-lg border p-4">
								<span :class="SECTION_LABEL">Worst failing checks</span>
								<n-spin :show="loadingTop">
									<p v-if="!topChecks.length && !loadingTop" class="text-secondary m-0 text-sm">No failing check.</p>
									<ol class="m-0 flex list-none flex-col gap-1 p-0">
										<li v-for="check of topChecks" :key="check.check_id">
											<button
												type="button"
												class="hover:bg-secondary/60 grid w-full grid-cols-[5.5rem_minmax(0,1fr)_3rem] items-center gap-3 rounded px-2 py-1.5 text-left"
												:disabled="scan.findings_pruned"
												@click="viewFindings(check.check_id)"
											>
												<n-tag :type="SEVERITY_TAGS[check.severity]" size="tiny" round :bordered="false" class="justify-self-start">
													{{ SEVERITY_LABELS[check.severity] }}
												</n-tag>
												<span class="truncate text-sm" :title="check.title"><bdi>{{ check.title || check.check_id }}</bdi></span>
												<span class="text-default text-right font-mono text-sm tabular-nums">{{ check.failed }}</span>
											</button>
										</li>
									</ol>
								</n-spin>
							</section>
						</div>
					</div>
				</n-tab-pane>
				<n-tab-pane name="findings" tab="Findings" display-directive="show:lazy" :disabled="scan.findings_pruned">
					<CloudFindings
						:customer-code
						:scan-id="scan.id"
						:check-id="checkQuery ?? null"
						:compared
						@clear-check="setQuery({ check: undefined })"
					/>
				</n-tab-pane>
				<n-tab-pane name="checks" tab="Checks" display-directive="show:lazy">
					<CloudChecks :customer-code :scan-id="scan.id" :findings-available="!scan.findings_pruned" @view-findings="viewFindings" />
				</n-tab-pane>
				<n-tab-pane name="compliance" tab="Compliance" display-directive="show:lazy">
					<CloudCompliance
						:customer-code
						:scan-id="scan.id"
						:framework="frameworkQuery ?? null"
						@open="key => setQuery({ framework: key })"
						@close="setQuery({ framework: undefined })"
					/>
				</n-tab-pane>
			</n-tabs>
		</template>
	</section>
</template>

<script setup lang="ts">
import type { CloudAccount, CloudCheck, CloudReportKind, CloudScan } from "@/types/cloud-assessment"
import type { ApiError } from "@/types/common"
import { saveAs } from "file-saver"
import { NAlert, NButton, NPopconfirm, NSpin, NTabPane, NTabs, NTag, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { useRouteQueryParam } from "@/composables/useNavigation"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import CloudChecks from "./CloudChecks.vue"
import CloudCompliance from "./CloudCompliance.vue"
import CloudFindings from "./CloudFindings.vue"
import CloudScanStatusTag from "./CloudScanStatusTag.vue"
import CloudSeverityBars from "./CloudSeverityBars.vue"
import { durationText, isActive, passRate, SEVERITY_LABELS, SEVERITY_TAGS } from "./utils"

const { customerCode, scan } = defineProps<{ customerCode: string; account: CloudAccount; scan: CloudScan }>()
const emit = defineEmits<{ (e: "changed"): void }>()

const TABS = ["overview", "findings", "checks", "compliance"] as const
const DownloadIcon = "carbon:download"

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const isAdmin = computed(() => useAuthStore().isAdmin)
const tabQuery = useRouteQueryParam("tab")
const checkQuery = useRouteQueryParam("check")
const frameworkQuery = useRouteQueryParam("framework")

const downloading = ref<CloudReportKind | null>(null)
const cancelling = ref(false)
const deleting = ref(false)
const topChecks = ref<CloudCheck[]>([])
const loadingTop = ref(false)

const active = computed(() => isActive(scan.status))
// A scan whose results are being stored has finished: nothing is left to cancel.
const cancellable = computed(() => active.value && scan.status !== "ingesting")
const duration = computed(() => durationText(scan.duration_seconds))
const activeText = computed(() => {
	if (scan.status === "queued") return "Waiting for copilot-prowler to take the scan."
	if (scan.status === "ingesting") return "Prowler finished: CoPilot is storing the results."
	return "Prowler is scanning. The results appear here when it completes; this page checks every few seconds."
})

/** Whether the new and resolved counts compare with anything: a first scan's compare with nothing. */
const compared = computed(() => scan.previous_scan_id !== null)

const tiles = computed(() => {
	const counts = scan.counts
	const rate = passRate(counts)
	const since = compared.value ? `since #${scan.previous_scan_id}` : "first scan"
	return [
		{ key: "rate", label: "Passing", value: rate === null ? "—" : `${rate}%`, tone: "text-default", hint: null },
		{ key: "failed", label: "Failed", value: counts.failed, tone: counts.failed ? "text-error" : "text-default", hint: null },
		{ key: "manual", label: "Manual review", value: counts.manual, tone: "text-default", hint: null },
		{ key: "muted", label: "Muted", value: counts.muted, tone: "text-default", hint: null },
		{
			key: "new",
			label: "New failures",
			value: compared.value ? counts.new_failed : "—",
			tone: compared.value && counts.new_failed ? "text-error" : "text-default",
			hint: since
		},
		{
			key: "resolved",
			label: "Resolved",
			value: compared.value ? counts.resolved_failed : "—",
			tone: compared.value && counts.resolved_failed ? "text-success" : "text-default",
			hint: since
		}
	]
})

function setQuery(patch: Record<string, string | undefined>) {
	router.replace({ query: { ...route.query, ...patch } })
}

const tabModel = computed<string>({
	get: () => ((TABS as readonly string[]).includes(tabQuery.value ?? "") ? (tabQuery.value as string) : "overview"),
	set: tab => setQuery({ tab, check: tab === "findings" ? checkQuery.value : undefined })
})

/** A check's findings: the Findings tab, filtered to it. A new place to go back from: push. */
function viewFindings(checkId: string) {
	router.push({ query: { ...route.query, tab: "findings", check: checkId } })
}

function loadTopChecks() {
	if (scan.status !== "completed") return
	loadingTop.value = true
	Api.cloudAssessment
		.getChecks(customerCode, scan.id, { status: "fail", page_size: 8 })
		.then(res => {
			topChecks.value = res.data.checks
		})
		.catch(() => {
			topChecks.value = []
		})
		.finally(() => {
			loadingTop.value = false
		})
}

function download(kind: CloudReportKind) {
	downloading.value = kind
	Api.cloudAssessment
		.downloadReport(customerCode, scan.id, kind)
		.then(res => {
			saveAs(res.data, `prowler-scan-${scan.id}.${kind}`)
		})
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "The report couldn't be downloaded.")
		})
		.finally(() => {
			downloading.value = null
		})
}

function cancel() {
	cancelling.value = true
	Api.cloudAssessment
		.cancelScan(customerCode, scan.id)
		.then(() => {
			message.success("Scan cancelled")
			emit("changed")
		})
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "The scan couldn't be cancelled.")
		})
		.finally(() => {
			cancelling.value = false
		})
}

function remove() {
	deleting.value = true
	Api.cloudAssessment
		.deleteScan(customerCode, scan.id)
		.then(() => {
			message.success("Scan deleted")
			setQuery({ scan: undefined, tab: undefined, check: undefined, framework: undefined })
			emit("changed")
		})
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "The scan couldn't be deleted.")
		})
		.finally(() => {
			deleting.value = false
		})
}

// Also when a scan the page is watching completes: the account's poll hands over the same scan, finished.
watch(
	() => scan.status,
	status => {
		if (status === "completed") loadTopChecks()
	},
	{ immediate: true }
)
</script>
