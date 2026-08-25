<template>
	<div class="border-default flex flex-col gap-1 rounded-lg border p-2">
		<div class="text-secondary flex items-center justify-between px-1 py-1 text-xs font-semibold">
			<span>Batch · {{ jobIds.length }} files</span>
			<span v-if="runningCount">{{ runningCount }} running</span>
		</div>
		<button
			v-for="b in items"
			:key="b.jobId"
			class="flex items-center gap-2 rounded-md px-2 py-2 text-left transition-colors"
			:class="b.jobId === activeJobId ? 'bg-secondary' : 'hover:bg-secondary'"
			@click="select(b.jobId)"
		>
			<Icon :name="iconFor(b)" :size="16" :class="colorFor(b)" class="shrink-0" />
			<span class="grow truncate text-sm" :class="{ 'font-medium': b.jobId === activeJobId }">
				{{ b.filename || "…" }}
			</span>
			<n-spin v-if="isRunning(b)" :size="12" />
			<n-tag v-else :type="verdictType(b.verdict)" size="small" round :bordered="false">
				{{ b.verdict || b.status || "—" }}
			</n-tag>
		</button>
	</div>
</template>

<script setup lang="ts">
import type { FileAnalysisJob, FileAnalysisVerdict } from "@/types/file-analysis"
import { NSpin, NTag } from "naive-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

interface BatchEntry {
	jobId: string
	filename: string
	verdict: FileAnalysisVerdict | null
	status: string
}

const props = defineProps<{ jobIds: string[]; activeJobId: string }>()
const router = useRouter()

const items = ref<BatchEntry[]>([])
let pollTimer: ReturnType<typeof setInterval> | null = null

const runningCount = computed(() => items.value.filter(isRunning).length)

function isRunning(b: BatchEntry): boolean {
	return ["pending", "queued", "running"].includes(b.status)
}

function verdictType(v: FileAnalysisVerdict | null): "success" | "warning" | "error" | "default" {
	if (v === "malicious") return "error"
	if (v === "suspicious") return "warning"
	if (v === "clean") return "success"
	return "default"
}

function iconFor(b: BatchEntry): string {
	if (isRunning(b)) return "carbon:document"
	if (b.status === "failed") return "carbon:warning"
	if (b.verdict === "malicious") return "carbon:warning-alt-filled"
	if (b.verdict === "suspicious") return "carbon:warning-alt"
	return "carbon:checkmark-filled"
}

function colorFor(b: BatchEntry): string {
	if (b.verdict === "malicious") return "text-red-500"
	if (b.verdict === "suspicious") return "text-amber-500"
	if (b.status === "failed") return "text-red-500"
	return "text-secondary"
}

function select(jobId: string) {
	if (jobId === props.activeJobId) return
	router.push({ name: "FileAnalysisDetails", params: { jobId }, query: { batch: props.jobIds.join(",") } })
}

function fetchAll() {
	Promise.all(
		props.jobIds.map(jobId =>
			Api.fileAnalysis
				.getJob(jobId)
				.then(res => {
					const j = res.data?.job as FileAnalysisJob | undefined
					return {
						jobId,
						filename: j?.filename || "",
						verdict: j?.verdict ?? null,
						status: j?.status || "pending"
					} as BatchEntry
				})
				.catch(() => ({ jobId, filename: "", verdict: null, status: "pending" }) as BatchEntry)
		)
	).then(entries => {
		items.value = entries
		if (!entries.some(isRunning)) stopPoll()
	})
}

function stopPoll() {
	if (pollTimer) {
		clearInterval(pollTimer)
		pollTimer = null
	}
}

watch(
	() => props.jobIds.join(","),
	() => {
		stopPoll()
		fetchAll()
		pollTimer = setInterval(fetchAll, 3000)
	},
	{ immediate: true }
)
onBeforeUnmount(stopPoll)
</script>
