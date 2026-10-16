<template>
	<div class="flex h-full gap-3 overflow-hidden" data-testid="talon-v2-chat">
		<div class="border-default flex w-64 shrink-0 flex-col gap-2 overflow-hidden border-r pr-3">
			<div class="flex items-center gap-2">
				<span class="grow text-sm font-semibold">Threads</span>
				<n-button
					size="tiny"
					type="primary"
					secondary
					data-testid="talon-v2-new-thread-button"
					@click="openPicker()"
				>
					<template #icon>
						<Icon name="carbon:add" />
					</template>
					New
				</n-button>
			</div>
			<SegmentedToggle
				v-model="statusFilter"
				:options="[
					{ value: 'active', label: 'Active' },
					{ value: 'archived', label: 'Archived' }
				]"
				label="Show"
				test-id="talon-v2-thread-filter"
			/>
			<n-scrollbar class="grow">
				<n-alert
					v-if="listError"
					type="error"
					:bordered="false"
					class="mb-2 text-xs"
					data-testid="talon-v2-list-error"
				>
					<div class="flex flex-col gap-1">
						<span>{{ listError }}</span>
						<n-button size="tiny" secondary @click="loadThreads()">Retry</n-button>
					</div>
				</n-alert>
				<TalonThreadList
					:threads
					:selected-id="picking ? null : (selected?.id ?? null)"
					:loading="listLoading"
					:has-more="!!listNext"
					@select="select"
					@rename="rename"
					@archive="archive"
					@load-more="loadThreads(true)"
				/>
			</n-scrollbar>
		</div>

		<div class="flex grow flex-col overflow-hidden">
			<TalonNewThread
				v-if="picking"
				:creating
				:error="createError"
				:cancellable="!!selected"
				@create="create"
				@cancel="picking = false"
			/>
			<TalonV2Conversation
				v-else-if="selected"
				:key="selected.id"
				:thread="selected"
				class="grow"
				@activity="onActivity"
				@gone="onGone"
			/>
			<div v-else-if="listLoading" class="flex grow items-center justify-center gap-2">
				<Icon name="svg-spinners:pulse-rings-3" :size="20" />
				<span class="text-tertiary text-sm">Loading threads...</span>
			</div>
			<div
				v-else
				class="text-tertiary flex grow items-center justify-center text-sm"
				data-testid="talon-v2-pick-thread"
			>
				Pick a thread, or start a new one.
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
// The Talon v2 chat (talon-analyst M5, behind the "Talon v2" setting): a thread rail and the
// selected thread's conversation. Threads are the caller's own, listed by talon-analyst; each is
// general or scoped to one customer, chosen once in the picker.
import type { TalonV2Thread, TalonV2ThreadCreate } from "@/types/talonV2"
import axios from "axios"
import { NAlert, NButton, NScrollbar, useMessage } from "naive-ui"
import { onBeforeUnmount, onMounted, ref, watch } from "vue"
import Api from "@/api"
import { refusalDetail } from "@/api/endpoints/talonV2"
import { TALON_V2_FAILED } from "@/api/talonV2Parser"
import Icon from "@/components/common/Icon.vue"
import SegmentedToggle from "@/components/common/SegmentedToggle.vue"
import TalonNewThread from "./TalonNewThread.vue"
import TalonThreadList from "./TalonThreadList.vue"
import TalonV2Conversation from "./TalonV2Conversation.vue"

const toast = useMessage()

/** Threads per list page (talon-analyst allows up to 200). */
const LIST_LIMIT = 50

const threads = ref<TalonV2Thread[]>([])
const selected = ref<TalonV2Thread | null>(null)
const statusFilter = ref<"active" | "archived">("active")
const listNext = ref<string | null>(null)
const listLoading = ref(false)
const listError = ref<string | null>(null)
const picking = ref(false)
const creating = ref(false)
const createError = ref<string | null>(null)

let listController: AbortController | null = null
/** A thread to select once the list (re)loads: one just created while archived threads showed. */
let preferId: string | null = null

function detailOf(err: unknown): string {
	return axios.isAxiosError(err) ? refusalDetail(err.response?.data) : TALON_V2_FAILED
}

async function loadThreads(more = false) {
	listController?.abort()
	const controller = new AbortController()
	listController = controller
	listLoading.value = true
	listError.value = null
	try {
		const res = await Api.talonV2.listThreads(
			{ status: statusFilter.value, limit: LIST_LIMIT, cursor: more ? listNext.value : null },
			controller.signal
		)
		if (controller.signal.aborted) return
		const page = res.data.threads || []
		threads.value = more ? [...threads.value, ...page.filter(t => !threads.value.some(s => s.id === t.id))] : page
		listNext.value = res.data.next ?? null
		if (!more) {
			const keepId = preferId ?? selected.value?.id
			preferId = null
			selected.value = threads.value.find(t => t.id === keepId) || threads.value[0] || null
			// Nothing to show yet: start with the picker.
			if (!selected.value && statusFilter.value === "active") picking.value = true
		}
	} catch (err) {
		if (controller.signal.aborted || axios.isCancel(err)) return
		listError.value = detailOf(err)
	} finally {
		if (listController === controller) {
			listLoading.value = false
			listController = null
		}
	}
}

function select(thread: TalonV2Thread) {
	picking.value = false
	selected.value = thread
}

function openPicker() {
	createError.value = null
	picking.value = true
}

function replace(thread: TalonV2Thread) {
	threads.value = threads.value.map(t => (t.id === thread.id ? thread : t))
	if (selected.value?.id === thread.id) selected.value = thread
}

async function create(payload: TalonV2ThreadCreate) {
	creating.value = true
	createError.value = null
	try {
		const res = await Api.talonV2.createThread(payload)
		const thread = res.data
		picking.value = false
		if (statusFilter.value !== "active") {
			// The active list reloads (the watcher) and opens the new thread.
			preferId = thread.id
			statusFilter.value = "active"
			return
		}
		threads.value = [thread, ...threads.value.filter(t => t.id !== thread.id)]
		selected.value = thread
	} catch (err) {
		createError.value = detailOf(err)
	} finally {
		creating.value = false
	}
}

async function rename(thread: TalonV2Thread, title: string | null) {
	try {
		const res = await Api.talonV2.renameThread(thread.id, title)
		replace(res.data)
	} catch (err) {
		toast.error(detailOf(err))
	}
}

async function archive(thread: TalonV2Thread) {
	try {
		await Api.talonV2.archiveThread(thread.id)
		const index = threads.value.findIndex(t => t.id === thread.id)
		threads.value = threads.value.filter(t => t.id !== thread.id)
		if (selected.value?.id === thread.id) {
			selected.value = threads.value[Math.min(index, threads.value.length - 1)] || null
			if (!selected.value) picking.value = true
		}
	} catch (err) {
		toast.error(detailOf(err))
	}
}

/** A turn completed: the thread moves to the top (newest activity first) with its new size. */
function onActivity(value: { id: string; context_tokens: number | null }) {
	const thread = threads.value.find(t => t.id === value.id)
	if (!thread) return
	const updated = { ...thread, context_tokens: value.context_tokens, updated_at: new Date().toISOString() }
	threads.value = [updated, ...threads.value.filter(t => t.id !== value.id)]
	if (selected.value?.id === value.id) selected.value = updated
}

function onGone(id: string) {
	threads.value = threads.value.filter(t => t.id !== id)
}

watch(statusFilter, () => {
	selected.value = null
	picking.value = false
	listNext.value = null
	loadThreads()
})

onMounted(() => loadThreads())
onBeforeUnmount(() => listController?.abort())
</script>
