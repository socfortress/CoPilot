<template>
	<div class="flex flex-col gap-2">
		<div class="flex items-center justify-between">
			<span class="text-sm font-semibold">Recent analyses</span>
			<n-button text size="tiny" :loading="loading" :disabled="!customerCode" @click="load()">
				<template #icon><Icon :name="RefreshIcon" :size="14" /></template>
				Refresh
			</n-button>
		</div>

		<n-spin v-if="loading && !items.length" show class="self-center py-4" />

		<n-empty
			v-else-if="!customerCode"
			size="small"
			description="Pick a customer to see its analysis history."
			class="py-4"
		/>
		<n-empty v-else-if="!items.length" size="small" description="No analyses yet for this customer." class="py-4" />

		<div v-else class="border-default flex flex-col divide-y divide-[var(--n-border-color)] rounded-lg border">
			<div
				v-for="it in items"
				:key="it.job_id"
				class="hover:bg-secondary flex cursor-pointer items-center gap-3 px-3 py-2 transition-colors"
				@click="open(it)"
			>
				<Icon :name="iconFor(it)" :size="18" class="text-secondary shrink-0" />
				<div class="flex min-w-0 grow flex-col">
					<span class="truncate text-sm font-medium">{{ it.filename || "(unnamed)" }}</span>
					<span class="text-secondary flex items-center gap-2 text-xs">
						<span>{{ sourceLabel(it.source) }}</span>
						<span>·</span>
						<span>{{ when(it.created_at) }}</span>
						<code class="opacity-70">{{ it.sha256.slice(0, 12) }}</code>
					</span>
				</div>
				<n-tag
					v-if="it.vt_total != null"
					size="small"
					round
					:bordered="false"
					:type="it.vt_malicious ? 'error' : 'default'"
				>
					VT {{ it.vt_malicious ?? 0 }}/{{ it.vt_total }}
				</n-tag>
				<n-tag :type="verdictType(it.verdict)" size="small" round :bordered="false">
					{{ it.verdict || it.status || "—" }}
				</n-tag>
				<Icon :name="ChevronIcon" :size="16" class="text-secondary shrink-0" />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { FileAnalysisHistoryItem, FileAnalysisVerdict } from "@/types/file-analysis"
import { NButton, NEmpty, NSpin, NTag, useMessage } from "naive-ui"
import { ref, watch } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{ customerCode: string; refreshKey?: number }>()

const router = useRouter()
const message = useMessage()

const RefreshIcon = "carbon:renew"
const ChevronIcon = "carbon:chevron-right"

const items = ref<FileAnalysisHistoryItem[]>([])
const loading = ref(false)

function verdictType(v: FileAnalysisVerdict | null): "success" | "warning" | "error" | "default" {
	if (v === "malicious") return "error"
	if (v === "suspicious") return "warning"
	if (v === "clean") return "success"
	return "default"
}

function iconFor(it: FileAnalysisHistoryItem): string {
	if (it.verdict === "malicious") return "carbon:warning-alt-filled"
	if (it.verdict === "suspicious") return "carbon:warning-alt"
	return "carbon:document"
}

function sourceLabel(source: string): string {
	if (source === "host_path") return "collected from endpoint"
	if (source === "flow") return "from flow"
	if (source === "upload") return "uploaded"
	return source || "—"
}

function when(iso: string): string {
	if (!iso) return ""
	const d = new Date(iso)
	if (Number.isNaN(d.getTime())) return iso
	return d.toLocaleString()
}

function open(it: FileAnalysisHistoryItem) {
	if (!it.job_id) return
	router.push({ name: "FileAnalysis", params: { jobId: it.job_id } })
}

function load() {
	if (!props.customerCode) {
		items.value = []
		return
	}
	loading.value = true
	Api.fileAnalysis
		.getHistory(props.customerCode)
		.then(res => {
			if (res.data.success) items.value = res.data.items || []
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Could not load history.")
		})
		.finally(() => {
			loading.value = false
		})
}

watch(() => props.customerCode, load, { immediate: true })
watch(
	() => props.refreshKey,
	() => load()
)
</script>
