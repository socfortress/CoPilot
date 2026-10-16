<template>
	<div class="flex h-full flex-col overflow-hidden" data-testid="talon-v2-conversation" :data-thread-id="thread.id">
		<div class="border-default flex items-center gap-2 border-b px-3 py-2">
			<Icon v-if="!thread.accessible" name="carbon:locked" :size="14" class="text-warning" />
			<span class="truncate text-sm font-semibold" data-testid="talon-v2-conversation-title">{{ title }}</span>
			<n-tag size="small" :bordered="false" data-testid="talon-v2-conversation-customer">
				{{ thread.customer_code ?? "General" }}
			</n-tag>
			<n-tag v-if="archived" size="small" :bordered="false" type="warning">Archived</n-tag>
			<span class="grow" />
			<TalonContextBadge :tokens="contextTokens" />
		</div>

		<n-scrollbar ref="scrollbar" class="grow">
			<div class="flex flex-col gap-6 p-3 pb-10">
				<div v-if="next && !loading" class="flex justify-center">
					<n-button
						size="tiny"
						secondary
						:loading="loadingOlder"
						data-testid="talon-v2-load-older"
						@click="loadOlder()"
					>
						Load older
					</n-button>
				</div>

				<div v-if="loading" class="flex items-center justify-center gap-2 py-8">
					<Icon name="svg-spinners:pulse-rings-3" :size="20" />
					<span class="text-tertiary text-sm">Loading the thread...</span>
				</div>
				<n-alert
					v-else-if="loadError"
					type="error"
					:bordered="false"
					class="text-sm"
					data-testid="talon-v2-load-error"
				>
					<div class="flex items-center gap-3">
						<span>{{ loadError }}</span>
						<n-button size="tiny" secondary @click="load()">Retry</n-button>
					</div>
				</n-alert>

				<TalonV2Message v-for="msg of messages" :key="msg.id" :message="msg" class="animate-fade" />

				<div
					v-if="!loading && !loadError && !messages.length && !notice"
					class="text-tertiary py-8 text-center text-sm"
					data-testid="talon-v2-empty"
				>
					{{
						thread.customer_code
							? `Ask Talon about ${thread.customer_code}'s alerts, assets and reports.`
							: "A general thread: Talon reads no customer data here."
					}}
				</div>
			</div>
		</n-scrollbar>

		<n-alert
			v-if="notice"
			:type="notice.kind === 'pending' || notice.kind === 'archived' ? 'warning' : 'error'"
			:bordered="false"
			class="mb-2 text-sm"
			data-testid="talon-v2-notice"
			:data-kind="notice.kind"
		>
			{{ notice.text }}
		</n-alert>

		<div class="relative flex flex-col overflow-hidden">
			<n-input
				v-model:value="input"
				class="max-h-full min-h-20 pt-1 pb-9"
				type="textarea"
				:placeholder="composerLocked ? 'This thread can\'t take new messages' : 'Ask Talon...'"
				:disabled="composerLocked"
				:autosize="{ minRows: 3, maxRows: 18 }"
				data-testid="talon-v2-input"
			/>
			<div class="absolute right-0 bottom-0 flex items-center p-2 pr-3">
				<n-button
					circle
					size="small"
					secondary
					:type="canSend ? 'primary' : undefined"
					:disabled="!canSend && !streaming"
					data-testid="talon-v2-send"
					@click="streaming ? stop() : send()"
				>
					<Icon :name="streaming ? 'carbon:stop-filled-alt' : 'carbon:arrow-up'" />
				</n-button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
// One v2 thread: its earlier turns from the read-back (`GET /talon/v2/threads/{id}/messages`,
// paged by cursor, "Load older"), and new turns streamed from `POST /talon/v2/chat/{id}`; both are
// folded into the same model (`talonV2Parser`), so a turn looks the same live and read back.
// Refusals keep their meaning: 409 is a decision pending, 403 a customer or alert access taken
// away (the composer is then disabled), 404 a thread that is gone.
import type { ScrollbarInst } from "naive-ui"
import type { ThreadNotice } from "./notices"
import type { TalonV2StreamResult } from "@/api/endpoints/talonV2"
import type { TalonV2ChatMessage, TalonV2Thread } from "@/types/talonV2"
import axios from "axios"
import { NAlert, NButton, NInput, NScrollbar, NTag } from "naive-ui"
import { nanoid } from "nanoid"
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue"
import Api from "@/api"
import { refusalDetail } from "@/api/endpoints/talonV2"
import {
	applyV2Chunk,
	endAssistantMessage,
	fromUIMessages,
	newAssistantMessage,
	newUserMessage,
	TALON_V2_FAILED
} from "@/api/talonV2Parser"
import Icon from "@/components/common/Icon.vue"
import { NOTICE_ARCHIVED, NOTICE_REVOKED, noticeFor } from "./notices"
import TalonContextBadge from "./TalonContextBadge.vue"
import TalonV2Message from "./TalonV2Message.vue"

const { thread } = defineProps<{ thread: TalonV2Thread }>()

const emit = defineEmits<{
	/** A turn completed: the thread's activity and context size moved. */
	(e: "activity", value: { id: string; context_tokens: number | null }): void
	/** The thread is gone (404): the list should drop it. */
	(e: "gone", id: string): void
}>()

/** Turns per read-back page (talon-analyst's default; at most 100). */
const PAGE_LIMIT = 20

const messages = ref<TalonV2ChatMessage[]>([])
const next = ref<string | null>(null)
const loading = ref(false)
const loadingOlder = ref(false)
const loadError = ref<string | null>(null)
const notice = ref<ThreadNotice | null>(null)
const contextTokens = ref<number | null>(thread.context_tokens ?? null)
const input = ref("")
const streaming = ref(false)
const scrollbar = ref<ScrollbarInst | null>(null)

let readController: AbortController | null = null
let streamController: AbortController | null = null

const title = computed(() => thread.title || "Untitled thread")
const archived = computed(() => thread.status === "archived")
const composerLocked = computed(
	() => archived.value || !thread.accessible || !!notice.value?.locksComposer || loading.value
)
const canSend = computed(() => !composerLocked.value && !streaming.value && !!input.value.trim())

function scrollToEnd() {
	nextTick(() => scrollbar.value?.scrollTo({ top: 99999999999999, behavior: "smooth" }))
}

function errorOf(err: unknown): { status: number | null; detail: string } {
	if (axios.isAxiosError(err)) {
		return { status: err.response?.status ?? null, detail: refusalDetail(err.response?.data) }
	}
	return { status: null, detail: TALON_V2_FAILED }
}

function baseNotice(): ThreadNotice | null {
	if (!thread.accessible) return { kind: "blocked", text: NOTICE_REVOKED, locksComposer: true }
	if (archived.value) return { kind: "archived", text: NOTICE_ARCHIVED, locksComposer: true }
	return null
}

/** The thread's newest page of turns. */
async function load() {
	readController?.abort()
	messages.value = []
	next.value = null
	loadError.value = null
	notice.value = baseNotice()
	contextTokens.value = thread.context_tokens ?? null
	// A thread whose customer was taken away can't be read either (403): no need to ask.
	if (!thread.accessible) return

	const controller = new AbortController()
	readController = controller
	loading.value = true
	try {
		const res = await Api.talonV2.getMessages(thread.id, { limit: PAGE_LIMIT }, controller.signal)
		if (controller.signal.aborted) return
		messages.value = fromUIMessages(res.data.messages)
		next.value = res.data.next ?? null
		contextTokens.value = res.data.thread?.context_tokens ?? contextTokens.value
		scrollToEnd()
	} catch (err) {
		if (controller.signal.aborted || axios.isCancel(err)) return
		const { status, detail } = errorOf(err)
		if (status === 403 || status === 404) {
			notice.value = noticeFor(status, detail)
			if (status === 404) emit("gone", thread.id)
		} else {
			loadError.value = detail
		}
	} finally {
		if (readController === controller) {
			loading.value = false
			readController = null
		}
	}
}

/** The page of turns before the oldest one shown. */
async function loadOlder() {
	if (!next.value || loadingOlder.value) return
	const threadId = thread.id
	loadingOlder.value = true
	try {
		const res = await Api.talonV2.getMessages(threadId, { limit: PAGE_LIMIT, before: next.value })
		if (threadId !== thread.id) return
		messages.value = [...fromUIMessages(res.data.messages), ...messages.value]
		next.value = res.data.next ?? null
	} catch (err) {
		if (threadId !== thread.id) return
		const { status, detail } = errorOf(err)
		if (status === 403 || status === 404) notice.value = noticeFor(status, detail)
		else loadError.value = detail
	} finally {
		loadingOlder.value = false
	}
}

/** The name of a call an earlier message showed (a resumed action call's answer has none). */
function knownToolName(toolCallId: string): string | null {
	for (const msg of messages.value) {
		for (const item of msg.items) {
			if (item.kind === "tool" && item.toolCallId === toolCallId && item.name) return item.name
		}
	}
	return null
}

async function send() {
	const text = input.value.trim()
	if (!text || !canSend.value) return

	const threadId = thread.id
	const messageId = `copilot-${nanoid()}`
	const now = new Date().toISOString()
	messages.value.push(newUserMessage(`local-${messageId}`, text, now))
	messages.value.push(newAssistantMessage(`local-${messageId}-reply`, now))
	// The reactive copy: chunks fold into what the template renders.
	const reply = messages.value[messages.value.length - 1]
	input.value = ""
	streaming.value = true
	if (notice.value && !notice.value.locksComposer) notice.value = null
	scrollToEnd()

	const controller = new AbortController()
	streamController = controller

	const onEnd = (result: TalonV2StreamResult) => {
		if (result.kind === "refused") {
			// Refused before anything ran: the message wasn't taken, so it goes back to the composer.
			messages.value = messages.value.filter(m => m.id !== reply.id && m.id !== `local-${messageId}`)
			if (!input.value) input.value = text
			notice.value = noticeFor(result.status, result.detail)
			if (result.status === 404) emit("gone", threadId)
			return
		}
		endAssistantMessage(reply, result.kind === "closed" ? "closed" : result.kind)
		const tokens = reply.usage?.context_tokens
		if (typeof tokens === "number") contextTokens.value = tokens
		if (reply.status === "completed") emit("activity", { id: threadId, context_tokens: contextTokens.value })
	}

	try {
		await Api.talonV2.streamChat(
			threadId,
			{ message: text, message_id: messageId },
			{
				onChunk: chunk => {
					applyV2Chunk(reply, chunk, { toolName: knownToolName })
					scrollToEnd()
				},
				onEnd
			},
			controller.signal
		)
	} catch {
		endAssistantMessage(reply, "closed")
	} finally {
		if (streamController === controller) {
			streaming.value = false
			streamController = null
		}
		scrollToEnd()
	}
}

function stop() {
	streamController?.abort()
}

watch(
	() => thread.id,
	() => {
		// Another thread: a reply in flight here is cut off, as leaving the page does.
		streamController?.abort()
		streamController = null
		streaming.value = false
		input.value = ""
		load()
	},
	{ immediate: true }
)

watch(
	() => [thread.accessible, thread.status],
	() => {
		// Archived or unarchived from the list while open.
		const base = baseNotice()
		if (base) notice.value = base
		else if (notice.value?.kind === "archived") notice.value = null
	}
)

// Nothing outlives the view: a stream left open would keep the turn running for nobody (#1072).
onBeforeUnmount(() => {
	readController?.abort()
	streamController?.abort()
})
</script>
