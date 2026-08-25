<template>
	<div class="flex flex-col gap-2">
		<div class="text-secondary flex items-center justify-between font-mono text-xs">
			<span>{{ jobIds.length }} files analysed together</span>
			<span v-if="!allLoaded">loading…</span>
			<span v-else-if="runningCount">{{ runningCount }} still running</span>
		</div>

		<CardEntity
			v-for="b in items"
			:key="b.jobId"
			clickable
			hoverable
			embedded
			size="small"
			:status="statusFor(b)"
			:highlighted="b.jobId === activeJobId"
			@click="select(b.jobId)"
		>
			<template #header>
				<div class="flex flex-wrap items-center gap-x-3 gap-y-2">
					<div class="flex min-w-0 grow basis-50 items-center gap-2">
						<Icon :name="iconFor(b)" :size="16" :class="colorFor(b)" class="shrink-0" />
						<span
							v-if="b.loaded"
							class="text-default truncate text-sm"
							:class="b.jobId === activeJobId ? 'font-semibold' : 'font-medium'"
							:title="b.filename"
						>
							{{ b.filename || "(unnamed)" }}
						</span>
						<n-skeleton v-else text :height="16" class="w-2/3" />
					</div>
					<div class="flex shrink-0 items-center gap-2">
						<n-skeleton v-if="!b.loaded" text :height="20" class="w-16" />
						<n-spin v-else-if="isRunning(b)" :size="13" />
						<n-tag v-else :type="verdictType(b.verdict)" size="small" round :bordered="false">
							{{ b.verdict || b.status || "—" }}
						</n-tag>
					</div>
				</div>
			</template>

			<template #default>
				<div class="flex flex-wrap items-center gap-2">
					<n-skeleton v-if="!b.loaded" text :height="22" class="w-40" />
					<Badge v-else type="splitted" size="small">
						<template #label>sha256</template>
						<template #value>
							<span class="font-mono">{{ b.sha256 ? b.sha256.slice(0, 12) : "—" }}</span>
						</template>
					</Badge>
					<Badge v-if="b.jobId === activeJobId" type="splitted" size="small" color="primary">
						<template #value>viewing</template>
					</Badge>
				</div>
			</template>
		</CardEntity>
	</div>
</template>

<script setup lang="ts">
import type { FileAnalysisJob, FileAnalysisVerdict } from "@/types/file-analysis"
import { NSkeleton, NSpin, NTag } from "naive-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"

interface BatchEntry {
	jobId: string
	/** False until this job's first fetch lands, so the row can show a placeholder. */
	loaded: boolean
	filename: string
	sha256: string
	verdict: FileAnalysisVerdict | null
	status: string
}

const props = defineProps<{ jobIds: string[]; activeJobId: string }>()

// The drawer that hosts this list closes on navigation, so the parent decides
// what "picking a job" means beyond the route change.
const emit = defineEmits<{ (e: "select", jobId: string): void }>()

const router = useRouter()

const items = ref<BatchEntry[]>([])
let pollTimer: ReturnType<typeof setInterval> | null = null

const runningCount = computed(() => items.value.filter(isRunning).length)
const allLoaded = computed(() => items.value.length > 0 && items.value.every(b => b.loaded))

function isRunning(b: BatchEntry): boolean {
	return b.loaded && ["pending", "queued", "running"].includes(b.status)
}

function verdictType(v: FileAnalysisVerdict | null): "success" | "warning" | "error" | "default" {
	if (v === "malicious") return "error"
	if (v === "suspicious") return "warning"
	if (v === "clean") return "success"
	return "default"
}

// Only a judged-bad row carries a status accent; a clean one stays neutral rather
// than painting the drawer green.
function statusFor(b: BatchEntry): "success" | "warning" | "error" | undefined {
	if (!b.loaded) return undefined
	if (b.status === "failed") return "error"
	if (b.verdict === "malicious") return "error"
	if (b.verdict === "suspicious") return "warning"
	return undefined
}

function iconFor(b: BatchEntry): string {
	if (isRunning(b)) return "carbon:document"
	if (b.status === "failed") return "carbon:warning"
	if (b.verdict === "malicious") return "carbon:warning-alt-filled"
	if (b.verdict === "suspicious") return "carbon:warning-alt"
	return "carbon:checkmark-filled"
}

function colorFor(b: BatchEntry): string {
	if (b.verdict === "malicious" || b.status === "failed") return "text-error"
	if (b.verdict === "suspicious") return "text-warning"
	return "text-secondary"
}

function select(jobId: string) {
	emit("select", jobId)
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
						loaded: true,
						filename: j?.filename || "",
						sha256: j?.sha256 || "",
						verdict: j?.verdict ?? null,
						status: j?.status || "pending"
					} as BatchEntry
				})
				// A job that cannot be read is still shown, as loaded-but-unknown: an
				// empty gap would be indistinguishable from a bug.
				.catch(
					() =>
						({ jobId, loaded: true, filename: "", sha256: "", verdict: null, status: "unknown" }) as BatchEntry
				)
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
		// Placeholders first: the drawer opens with one row per job right away.
		// Waiting for Promise.all left it blank for a beat, which reads as broken.
		items.value = props.jobIds.map(jobId => ({
			jobId,
			loaded: false,
			filename: "",
			sha256: "",
			verdict: null,
			status: "pending"
		}))
		fetchAll()
		pollTimer = setInterval(fetchAll, 3000)
	},
	{ immediate: true }
)
onBeforeUnmount(stopPoll)
</script>
