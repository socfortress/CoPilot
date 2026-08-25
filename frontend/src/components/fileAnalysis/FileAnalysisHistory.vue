<template>
	<div class="flex flex-col gap-2">
		<!-- Filters the loaded rows as you type; a full SHA256 additionally asks the
		     backend whether this customer has a cached analysis older than the page. -->
		<n-input
			v-model:value="query"
			size="small"
			clearable
			:disabled="!customerCode"
			:loading="looking"
			placeholder="Filter by name, or paste a full SHA256 to look one up"
			@keyup.enter="lookup()"
		>
			<template #prefix><Icon :name="SearchIcon" :size="14" /></template>
			<template v-if="isFullHash" #suffix>
				<n-button text size="tiny" :loading="looking" @click="lookup()">Look up</n-button>
			</template>
		</n-input>

		<n-spin v-if="loading && !items.length" show class="self-center py-4" />

		<n-empty
			v-else-if="!customerCode"
			size="small"
			description="Pick a customer to see its analysis history."
			class="py-4"
		/>
		<n-empty v-else-if="!items.length" size="small" description="No analyses yet for this customer." class="py-4" />
		<n-empty
			v-else-if="!visibleItems.length"
			size="small"
			:description="
				isFullHash
					? 'Not in the loaded rows — press Look up to search this customer\'s cache.'
					: 'No analysis matches that filter.'
			"
			class="py-4"
		/>

		<!-- Responsive by intrinsic sizing rather than viewport breakpoints: this list
		     lives in a drawer whose width is independent of the screen, so media
		     queries would fire on the wrong measurement. The title claims a basis of
		     12.5rem and the rest flex-wraps, so each row reflows against the box it is
		     actually in — verified down to a 340px drawer with no overflow. -->
		<div v-else class="flex flex-col gap-2">
			<CardEntity
				v-for="it in visibleItems"
				:key="it.job_id"
				clickable
				hoverable
				embedded
				size="small"
				:status="statusFor(it.verdict)"
				@click="open(it)"
			>
				<!-- One header slot rather than headerMain/headerExtra: the split wraps its
				     two halves in divs with no min-w-0, so a 64-char hash filename cannot
				     shrink and overflows the drawer instead of truncating. -->
				<template #header>
					<div class="flex flex-wrap items-center gap-x-3 gap-y-2">
						<div class="flex min-w-0 grow basis-50 items-center gap-2">
							<Icon :name="iconFor(it)" :size="16" class="text-secondary shrink-0" />
							<span class="text-default truncate text-sm font-medium" :title="it.filename">
								{{ it.filename || "(unnamed)" }}
							</span>
						</div>

						<div class="flex shrink-0 items-center gap-2">
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
							<n-popconfirm @positive-click="remove(it)">
								<template #trigger>
									<n-button
										text
										size="tiny"
										class="text-secondary hover:text-error-color"
										:loading="deletingId === it.job_id"
										title="Delete this analysis"
										@click.stop
									>
										<template #icon><Icon :name="TrashIcon" :size="15" /></template>
									</n-button>
								</template>
								Delete this analysis? The stored result and previews are removed (the file can be
								re-analysed later).
							</n-popconfirm>
						</div>
					</div>
				</template>

				<!-- Wrapping badges rather than fixed columns: "collected from endpoint" is
				     three times the width of "uploaded", so any grid sized for one of them
				     cramps the other. -->
				<template #default>
					<div class="flex flex-wrap items-center gap-2">
						<Badge type="splitted" :color="sourceColor(it.source)" size="small">
							<template #iconLeft><Icon :name="sourceIcon(it.source)" :size="12" /></template>
							<template #value>{{ sourceLabel(it.source) }}</template>
						</Badge>
						<Badge type="splitted" size="small">
							<template #iconLeft><Icon :name="TimeIcon" :size="12" /></template>
							<template #value>{{ formatDate(it.created_at, dFormats.datetimesec) }}</template>
						</Badge>
						<Badge type="splitted" size="small">
							<template #label>sha256</template>
							<template #value>
								<span class="font-mono">{{ it.sha256.slice(0, 12) }}</span>
							</template>
						</Badge>
					</div>
				</template>
			</CardEntity>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { FileAnalysisHistoryItem, FileAnalysisVerdict } from "@/types/file-analysis"
import { NButton, NEmpty, NInput, NPopconfirm, NSpin, NTag, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const props = defineProps<{ customerCode: string; refreshKey?: number }>()

const router = useRouter()
const message = useMessage()
const dFormats = useSettingsStore().dateFormat

const TrashIcon = "carbon:trash-can"
const TimeIcon = "carbon:time"
const UploadIcon = "carbon:cloud-upload"
const EndpointIcon = "carbon:bare-metal-server"
const SearchIcon = "carbon:search"
const SHA256_RE = /^[a-f0-9]{64}$/i

const items = ref<FileAnalysisHistoryItem[]>([])
const loading = ref(false)
const deletingId = ref<string | null>(null)
const query = ref("")
const looking = ref(false)

const isFullHash = computed(() => SHA256_RE.test(query.value.trim()))

const visibleItems = computed(() => {
	const q = query.value.trim().toLowerCase()
	if (!q) return items.value
	return items.value.filter(it => it.filename?.toLowerCase().includes(q) || it.sha256?.toLowerCase().startsWith(q))
})

// A cache hit can predate the history window (the backend keys the cache on
// sha256, the history on recency), so the lookup goes to the server rather than
// only filtering what is already on screen.
function lookup() {
	const sha = query.value.trim().toLowerCase()
	if (!props.customerCode || !isFullHash.value || looking.value) return

	const local = items.value.find(it => it.sha256?.toLowerCase() === sha)
	if (local) {
		open(local)
		return
	}

	looking.value = true
	Api.fileAnalysis
		.search(sha, props.customerCode)
		.then(res => {
			const jobId = res.data.job_id
			if (jobId) {
				router.push({ name: "FileAnalysisDetails", params: { jobId } })
			} else {
				message.info("This customer has no analysis for that hash yet.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Could not look up that hash.")
		})
		.finally(() => {
			looking.value = false
		})
}

function verdictType(v: FileAnalysisVerdict | null): "success" | "warning" | "error" | "default" {
	if (v === "malicious") return "error"
	if (v === "suspicious") return "warning"
	if (v === "clean") return "success"
	return "default"
}

// CardEntity paints its own status accent; only a judged-bad row should carry one,
// so an unjudged/clean row stays neutral instead of shouting "success".
function statusFor(v: FileAnalysisVerdict | null): "success" | "warning" | "error" | undefined {
	if (v === "malicious") return "error"
	if (v === "suspicious") return "warning"
	return undefined
}

function sourceIcon(source: string): string {
	return source === "upload" ? UploadIcon : EndpointIcon
}

function sourceColor(source: string): "primary" | undefined {
	return source === "upload" ? undefined : "primary"
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

function open(it: FileAnalysisHistoryItem) {
	if (!it.job_id) return
	router.push({ name: "FileAnalysisDetails", params: { jobId: it.job_id } })
}

function remove(it: FileAnalysisHistoryItem) {
	if (!it.job_id || deletingId.value) return
	deletingId.value = it.job_id
	Api.fileAnalysis
		.deleteAnalysis(it.job_id)
		.then(res => {
			if (res.data.success) {
				items.value = items.value.filter(x => x.job_id !== it.job_id)
				message.success("Analysis deleted.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Could not delete the analysis.")
		})
		.finally(() => {
			deletingId.value = null
		})
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

watch(
	() => props.customerCode,
	() => {
		query.value = ""
		load()
	},
	{ immediate: true }
)
watch(
	() => props.refreshKey,
	() => load()
)
</script>
