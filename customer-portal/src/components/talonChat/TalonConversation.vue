<template>
	<div class="flex min-h-0 flex-col gap-4" data-testid="talon-conversation">
		<div v-if="thread" class="flex flex-wrap items-center gap-2 text-sm">
			<h2 class="m-0 truncate text-base font-semibold" data-testid="talon-conversation-title">{{ title }}</h2>
			<span class="text-secondary text-xs">{{ customerName(thread.customer_code) }}</span>
			<RouterLink
				v-if="thread.context_alert_id"
				:to="{ name: 'AlertDetails', params: { id: thread.context_alert_id } }"
				class="text-primary text-xs"
				data-testid="talon-conversation-alert"
			>
				{{ $t("talonChat.conversation.aboutAlert", { id: thread.context_alert_id }) }}
			</RouterLink>
		</div>

		<n-alert v-if="loadErrorCode && !messages.length" type="warning" :bordered="false" data-testid="talon-conversation-load-error">
			<div class="flex flex-wrap items-center justify-between gap-3">
				<span>{{ errorText(loadErrorCode) }}</span>
				<n-button size="small" secondary @click="loadNewest()">{{ $t("common.actions.tryAgain") }}</n-button>
			</div>
		</n-alert>

		<div class="flex flex-col gap-4" aria-live="polite">
			<div v-if="olderCursor" class="flex justify-center">
				<n-button size="small" secondary :loading="loadingOlder" data-testid="talon-conversation-earlier" @click="loadOlder()">
					{{ $t("talonChat.conversation.loadEarlier") }}
				</n-button>
			</div>

			<p v-if="!loading && !messages.length && !loadErrorCode" class="text-secondary m-0 text-sm" data-testid="talon-conversation-empty">
				{{ $t("talonChat.conversation.empty") }}
			</p>
			<div v-if="loading && !messages.length" class="flex justify-center py-6"><n-spin size="small" /></div>

			<TalonMessage
				v-for="message of messages"
				:key="message.id"
				:message
				:show-cards="!readOnly"
				:can-draft="!readOnly && !!availability?.can_draft"
				:can-request-analysis="!readOnly && !!availability?.can_request_analysis"
				:feedback-busy="feedbackBusy.has(message.id)"
				@feedback="rating => rate(message, rating)"
			/>
		</div>

		<p v-if="thread && !thread.accessible" class="text-secondary m-0 text-sm" data-testid="talon-conversation-not-accessible">
			{{ $t("talonChat.conversation.notAccessible") }}
		</p>

		<form v-else class="flex flex-col gap-2" data-testid="talon-composer" @submit.prevent="send()">
			<n-alert v-if="sendErrorCode" type="error" :bordered="false" closable data-testid="talon-send-error" @close="sendErrorCode = null">
				{{ errorText(sendErrorCode) }}
			</n-alert>
			<n-input
				v-model:value="draft"
				type="textarea"
				:autosize="{ minRows: 2, maxRows: 8 }"
				:placeholder="$t('talonChat.conversation.placeholder')"
				:status="tooLong ? 'error' : undefined"
				:disabled="streaming || !thread"
				:input-props="{ 'aria-label': $t('talonChat.conversation.inputLabel') }"
				data-testid="talon-composer-input"
				@keydown="onKeydown"
			/>
			<div class="flex flex-wrap items-center justify-between gap-2">
				<span class="text-xs tabular-nums" :class="tooLong ? 'text-error' : 'text-secondary'" data-testid="talon-composer-count">
					<template v-if="tooLong">{{ $t("talonChat.conversation.tooLong", { max: MESSAGE_MAX }) }} · </template>{{ length }} / {{ MESSAGE_MAX }}
				</span>
				<n-button
					type="primary"
					attr-type="submit"
					:loading="streaming"
					:disabled="streaming || !thread || !length || tooLong"
					data-testid="talon-composer-send"
				>
					<template #icon><Icon name="carbon:send" /></template>
					{{ $t("talonChat.conversation.send") }}
				</n-button>
			</div>
		</form>
	</div>
</template>

<script setup lang="ts">
import type { TalonChatAvailability, TalonChatMessage, TalonChatRating, TalonChatThread } from "@/types/talonChat"
import { NAlert, NButton, NInput, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import { useI18n } from "vue-i18n"
import { RouterLink } from "vue-router"
import Api from "@/api"
import { applyChunk, endAssistantMessage, fromUIMessages, newAssistantMessage, newUserMessage } from "@/api/talonChatStream"
import Icon from "@/components/common/Icon.vue"
import { useCustomers } from "@/composables/common/useCustomers"
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { useReadOnly } from "@/composables/common/useReadOnly"
import { useTalonChatAvailability } from "@/composables/common/useTalonChatAvailability"
import { errorCodeOf, errorText, MESSAGE_MAX, messageLength, threadTitle } from "./talonChat"
import TalonMessage from "./TalonMessage.vue"

/**
 * One "Ask Talon" conversation: its turns read back from CoPilot (newest page first), and a new
 * message streamed in. Once a streamed turn completes it is read back, which gives it its run id
 * (for feedback) and the cards' current state. A refusal before the stream gives the message back
 * to the composer and says why, by its code.
 */
const { threadId } = defineProps<{ threadId: string }>()

const emit = defineEmits<{
	/** A turn ended: the thread's title or order in the list may have changed. */
	turn: []
}>()

const { t } = useI18n()
const toast = useMessage()
const { customerName } = useCustomers()
const { availabilityFor } = useTalonChatAvailability()

const PAGE_SIZE = 20

const thread = ref<TalonChatThread | null>(null)
const messages = ref<TalonChatMessage[]>([])
const olderCursor = ref<string | null>(null)
const loadErrorCode = ref<string | null>(null)
const { loading, run } = useLatestRequest()
const loadingOlder = ref(false)

const availability = ref<TalonChatAvailability | null>(null)
// May only read the thread's customer (#1312): chatting is reading, but no card is offered.
const readOnly = useReadOnly(() => thread.value?.customer_code)

const draft = ref("")
const streaming = ref(false)
const sendErrorCode = ref<string | null>(null)
let controller: AbortController | null = null
let localSeq = 0

const feedbackBusy = ref(new Set<string>())

const length = computed(() => messageLength(draft.value))
const tooLong = computed(() => length.value > MESSAGE_MAX)
const title = computed(() => {
	return thread.value ? threadTitle(thread.value) : ""
})

function isLocal(message: TalonChatMessage) {
	return message.id.startsWith("local-")
}

async function setThread(next: TalonChatThread) {
	const changed = thread.value?.customer_code !== next.customer_code
	thread.value = next
	if (changed) availability.value = await availabilityFor(next.customer_code)
}

/** Read the newest page. Older pages already shown stay; the local copy of a streamed turn goes. */
function loadNewest() {
	loadErrorCode.value = null
	return run(
		async signal => {
			const res = await Api.talonChat.getMessages(threadId, { limit: PAGE_SIZE }, signal)
			const fresh = fromUIMessages(res.data.messages)
			const freshIds = new Set(fresh.map(m => m.id))
			const kept = messages.value.filter(m => !isLocal(m) && !freshIds.has(m.id))
			const hadOlder = kept.length > 0
			messages.value = [...kept, ...fresh]
			if (!hadOlder) olderCursor.value = res.data.next ?? null
			if (res.data.thread) await setThread(res.data.thread)
		},
		err => {
			loadErrorCode.value = errorCodeOf(err) ?? "unknown"
		}
	)
}

async function loadOlder() {
	if (!olderCursor.value) return
	loadingOlder.value = true
	try {
		const res = await Api.talonChat.getMessages(threadId, { limit: PAGE_SIZE, before: olderCursor.value })
		const shown = new Set(messages.value.map(m => m.id))
		const older = fromUIMessages(res.data.messages).filter(m => !shown.has(m.id))
		messages.value = [...older, ...messages.value]
		olderCursor.value = res.data.next ?? null
	} catch (err) {
		toast.error(errorText(errorCodeOf(err)))
	} finally {
		loadingOlder.value = false
	}
}

function onKeydown(event: KeyboardEvent) {
	// Enter writes a new line; Ctrl or Cmd with Enter sends.
	if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
		event.preventDefault()
		send()
	}
}

async function send() {
	const text = draft.value.trim()
	if (!text || tooLong.value || streaming.value || !thread.value) return

	sendErrorCode.value = null
	streaming.value = true
	const seq = ++localSeq
	messages.value.push(newUserMessage(`local-${seq}-user`, text), newAssistantMessage(`local-${seq}-assistant`))
	// The reactive copy: what the template renders, so each chunk shows as it arrives.
	const assistant = messages.value[messages.value.length - 1] as TalonChatMessage
	draft.value = ""

	controller = new AbortController()
	let refused = false
	await Api.talonChat.streamChat(
		threadId,
		text,
		{
			onChunk: chunk => applyChunk(assistant, chunk),
			onEnd: result => {
				if (result.kind === "refused") {
					refused = true
					// Nothing was recorded: take the turn back, and give the user their message back.
					messages.value = messages.value.filter(m => m.id !== `local-${seq}-user` && m.id !== assistant.id)
					if (!draft.value) draft.value = text
					sendErrorCode.value = result.code ?? (result.status === null ? "network" : "unknown")
					return
				}
				endAssistantMessage(assistant, result.kind)
			}
		},
		controller.signal
	)
	controller = null
	streaming.value = false
	if (refused) return
	emit("turn")
	// A completed turn is read back: its run id (feedback) and the cards' state come from there.
	// A failed one keeps its own code on screen.
	if (assistant.status === "completed") await loadNewest()
}

async function rate(message: TalonChatMessage, rating: TalonChatRating | null) {
	if (!message.runId || feedbackBusy.value.has(message.id)) return
	const before = message.feedback
	message.feedback = rating
	feedbackBusy.value = new Set(feedbackBusy.value).add(message.id)
	try {
		await Api.talonChat.sendFeedback(threadId, message.runId, rating)
	} catch {
		message.feedback = before
		toast.error(t("talonChat.feedback.failed"))
	} finally {
		const next = new Set(feedbackBusy.value)
		next.delete(message.id)
		feedbackBusy.value = next
	}
}

watch(
	() => threadId,
	() => {
		controller?.abort()
		thread.value = null
		messages.value = []
		olderCursor.value = null
		availability.value = null
		draft.value = ""
		sendErrorCode.value = null
		loadNewest()
	},
	{ immediate: true }
)

// Leaving cuts the reply off (talon-analyst records it and frees the thread).
onBeforeUnmount(() => controller?.abort())
</script>
