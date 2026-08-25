<template>
	<header class="flex flex-col gap-3">
		<div class="flex flex-wrap items-center gap-x-4 gap-y-3">
			<!-- Identity. The verdict lives here and nowhere else — it used to be
			     repeated as a headline inside the summary card, opening the page with
			     the same word twice at two different sizes. -->
			<div class="flex min-w-0 grow basis-72 items-center gap-3">
				<!-- Verdict leads the row. Trailing the filename put it hard against the
				     action buttons, because the name grows to fill the row — and in this
				     feature names are often 64-char hashes, so that was the normal case,
				     not the edge one. Leading also matches how the page is read: what
				     the file turned out to be, then which file it was. -->
				<n-tag :type="verdictTagType" size="medium" round :bordered="false" class="shrink-0">
					<template #icon><Icon :name="verdictIcon" :size="14" /></template>
					<span class="capitalize">{{ verdict }}</span>
				</n-tag>

				<Icon :name="iconForFile(job?.filename)" :size="20" class="text-secondary shrink-0" />

				<h1 class="text-default min-w-0 grow truncate text-lg font-semibold" :title="job?.filename">
					{{ job?.filename || "File analysis" }}
				</h1>

				<n-spin v-if="running" :size="14" class="shrink-0" />
			</div>

			<!-- Actions as one segmented object rather than a bordered column: a column
			     claimed a whole empty row whenever only one action existed, and the
			     group separates by SHAPE (joined rectangles vs round tag and flat
			     chips) so it holds up with one, two or three buttons. -->
			<n-button-group size="small" class="ml-auto shrink-0">
				<n-button v-if="batchCount > 1" secondary @click="emit('openBatch')">
					<template #icon><Icon :name="BatchIcon" :size="15" /></template>
					<!-- Labels drop below sm so three buttons still fit a phone. -->
					<span class="hidden sm:inline">Batch · {{ batchCount }}</span>
				</n-button>
				<n-button v-if="job?.job_id" secondary :loading="downloadingPdf" @click="downloadPdf()">
					<template #icon><Icon :name="PdfIcon" :size="15" /></template>
					<span class="hidden sm:inline">PDF report</span>
				</n-button>
			</n-button-group>
		</div>

		<!-- One uniform strip of facts. Every chip is the same component at the same
		     size, so the eye reads a row rather than five competing treatments. -->
		<div class="flex flex-wrap items-center gap-2">
			<Badge v-if="job?.customer_code" type="splitted" size="small">
				<template #iconLeft><Icon :name="CustomerIcon" :size="12" /></template>
				<template #label>customer</template>
				<template #value>{{ job.customer_code }}</template>
			</Badge>

			<Badge v-if="job?.source" type="splitted" size="small">
				<template #iconLeft><Icon :name="sourceIcon" :size="12" /></template>
				<template #value>{{ sourceLabel }}</template>
			</Badge>

			<Badge v-if="job?.created_at" type="splitted" size="small">
				<template #iconLeft><Icon :name="TimeIcon" :size="12" /></template>
				<template #value>{{ formatDate(job.created_at, dFormats.datetimesec) }}</template>
			</Badge>

			<Badge v-if="sha256" type="splitted" size="small" hint-cursor @click="copySha()">
				<template #label>sha256</template>
				<template #value>
					<span class="font-mono">{{ sha256.slice(0, 16) }}</span>
				</template>
				<template #iconRight><Icon :name="CopyIcon" :size="12" /></template>
			</Badge>

			<!-- Only the reassuring case is a chip; an unhardened result gets the full
			     warning below instead, so the fact is never stated twice. -->
			<Badge v-if="hardened !== false" type="splitted" size="small" color="success">
				<template #iconLeft><Icon :name="ShieldIcon" :size="12" /></template>
				<template #value>isolated</template>
			</Badge>
		</div>
	</header>
</template>

<script setup lang="ts">
import type { FileAnalysisJob, FileAnalysisResult, FileAnalysisVerdict } from "@/types/file-analysis"
import { NButton, NButtonGroup, NSpin, NTag, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import { iconForFile } from "@/components/fileAnalysis/fileAnalysis.helpers"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	job?: FileAnalysisJob | null
	result?: FileAnalysisResult | null
	batchCount?: number
	running?: boolean
}>()

const emit = defineEmits<{ (e: "openBatch"): void }>()

const message = useMessage()
const dFormats = useSettingsStore().dateFormat

const CustomerIcon = "carbon:user"
const TimeIcon = "carbon:time"
const CopyIcon = "carbon:copy"
const ShieldIcon = "carbon:security"
const PdfIcon = "carbon:document-pdf"
const BatchIcon = "carbon:list"
const UploadIcon = "carbon:cloud-upload"
const EndpointIcon = "carbon:bare-metal-server"

const batchCount = computed(() => props.batchCount ?? 0)
const sha256 = computed(() => props.job?.sha256 || props.result?.inspector?.sha256 || "")
const hardened = computed(() => props.job?.hardened ?? props.result?.inspector?.hardened)

const verdict = computed<FileAnalysisVerdict>(
	() => props.job?.verdict || (props.result?.inspector?.verdict_hint as FileAnalysisVerdict) || "clean"
)

const verdictTagType = computed<"error" | "warning" | "success">(() => {
	if (verdict.value === "malicious") return "error"
	if (verdict.value === "suspicious") return "warning"
	return "success"
})

const verdictIcon = computed(() => {
	if (verdict.value === "malicious") return "carbon:warning-alt-filled"
	if (verdict.value === "suspicious") return "carbon:warning-alt"
	return "carbon:checkmark-filled"
})

const sourceIcon = computed(() => (props.job?.source === "upload" ? UploadIcon : EndpointIcon))
const sourceLabel = computed(() => {
	if (props.job?.source === "upload") return "uploaded"
	if (props.job?.source === "host_path") return "collected from endpoint"
	return props.job?.source || ""
})

function copySha() {
	if (!sha256.value) return
	navigator.clipboard.writeText(sha256.value)
	message.success("SHA256 copied.")
}

const downloadingPdf = ref(false)
function downloadPdf() {
	const id = props.job?.job_id
	if (!id || downloadingPdf.value) return
	downloadingPdf.value = true
	Api.fileAnalysis
		.getReportPdf(id)
		.then(res => {
			const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }))
			const a = document.createElement("a")
			a.href = url
			a.download = `file-analysis-${id}.pdf`
			a.click()
			URL.revokeObjectURL(url)
		})
		.catch(() => message.error("Could not generate the PDF report. Is the PDF renderer installed on the host?"))
		.finally(() => {
			downloadingPdf.value = false
		})
}
</script>
