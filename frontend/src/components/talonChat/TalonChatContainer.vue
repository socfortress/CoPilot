<template>
	<div class="flex h-full flex-col overflow-hidden">
		<n-scrollbar ref="scrollbar" class="grow">
			<div v-if="messages.length" class="flex flex-col gap-6 pb-20">
				<TalonChatBubble v-for="msg of messages" :key="msg.id" :msg class="animate-fade" />

				<div v-if="streaming" class="group animate-fade flex flex-col gap-0.5">
					<div class="text-secondary inline-flex items-center gap-1 text-sm font-semibold">
						<span>Talon:</span>
					</div>
					<div v-if="streamBuffer" class="**:text-default **:text-sm [&_*:last-child]:mb-0!">
						<Markdown :source="streamBuffer" class="overflow-hidden" />
					</div>
					<div v-else class="animate-fade flex items-center gap-2">
						<Icon name="svg-spinners:pulse-rings-3" :size="20" />
						<span class="text-tertiary text-sm">Thinking...</span>
					</div>
				</div>
			</div>
			<div v-else class="animate-fade flex flex-col items-center justify-center py-12">
				<TalonChatExample @example="useExample" />
			</div>
		</n-scrollbar>

		<TalonChatQuery
			v-model:input="input"
			:loading="streaming"
			:resetting
			:context-tokens
			@message="sendMessage"
			@stop="stopStream()"
			@clear-chat="clearChat()"
		/>
	</div>
</template>

<script setup lang="ts">
import type { ScrollbarInst } from "naive-ui"
import type { Message } from "./TalonChatQuery.vue"
import { useStorage } from "@vueuse/core"
import { NScrollbar, useMessage } from "naive-ui"
import { nanoid } from "nanoid"
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import Markdown from "@/components/common/Markdown.vue"
import { secureLocalStorage } from "@/utils/secure-storage"
import TalonChatBubble from "./TalonChatBubble.vue"
import TalonChatExample from "./TalonChatExample.vue"
import TalonChatQuery from "./TalonChatQuery.vue"

interface TalonMessage {
	id: string
	datetime: Date
	body: string
	sender: "user" | "server"
}

const message = useMessage()

const messages = useStorage<TalonMessage[]>("talon-chat-messages", [], secureLocalStorage({ session: true }))
const input = ref("")
const streaming = ref(false)
const streamBuffer = ref("")
const scrollbar = ref<ScrollbarInst | null>(null)
const resetting = ref(false)
// Size of the conversation Talon is carrying. Surfaced because a resumed
// session grows without bound: past a few hundred thousand tokens replies
// slow to minutes, and there is otherwise nothing to tell the analyst why.
const contextTokens = ref<number | null>(null)

let abortController: AbortController | null = null

function useExample(example: string) {
	input.value = example
	sendMessage({ input: example })
}

async function clearChat() {
	if (resetting.value) return

	resetting.value = true
	try {
		// Reset Talon first. Emptying the local list on a failed reset would
		// report success while the agent still holds every prior turn.
		await Api.talon.resetSession()
		messages.value = []
		contextTokens.value = null
	} catch {
		message.error("Couldn't start a new session. Talon still has the previous conversation.")
	} finally {
		resetting.value = false
	}
}

async function loadContextSize() {
	try {
		const res = await Api.talon.getSessionContext()
		contextTokens.value = res.data?.input_tokens ?? null
	} catch {
		// Advisory only — a status hiccup must not disturb the chat.
		contextTokens.value = null
	}
}

onMounted(loadContextSize)

function scrollChat() {
	nextTick(() => {
		scrollbar.value?.scrollTo({ top: 99999999999999, behavior: "smooth" })
	})
}

async function sendMessage(payload: Message) {
	const text = payload.input.trim()
	if (!text || streaming.value) return

	messages.value.push({
		id: nanoid(),
		datetime: new Date(),
		body: text,
		sender: "user"
	})

	input.value = ""
	streaming.value = true
	streamBuffer.value = ""
	scrollChat()

	abortController = new AbortController()

	try {
		await Api.talon.streamMessage(
			text,
			(chunk: string) => {
				streamBuffer.value += chunk
				scrollChat()
			},
			() => {
				if (streamBuffer.value) {
					messages.value.push({
						id: nanoid(),
						datetime: new Date(),
						body: streamBuffer.value,
						sender: "server"
					})
				}
				streaming.value = false
				streamBuffer.value = ""
				scrollChat()
				loadContextSize()
			},
			(err: string) => {
				if (err !== "AbortError") {
					message.error("An error occurred. Please try again.")
				}
				streaming.value = false
				streamBuffer.value = ""
				scrollChat()
			},
			abortController.signal
		)
	} catch {
		streaming.value = false
		streamBuffer.value = ""
	}
}

function stopStream() {
	abortController?.abort()

	if (streamBuffer.value) {
		messages.value.push({
			id: nanoid(),
			datetime: new Date(),
			body: streamBuffer.value,
			sender: "server"
		})
	}

	streaming.value = false
	streamBuffer.value = ""
	scrollChat()
}

defineExpose({
	// Same contract as the in-chat control: a caller asking to clear the history
	// means "start a new conversation", not "hide the transcript".
	clearHistory: clearChat
})

// Cancel anything still in flight when this component goes away: without it the
// request outlives the view — the backend keeps working for a page nobody is
// looking at, and the response resolves into a destroyed scope (#1072).
onBeforeUnmount(() => {
	abortController?.abort()
})
</script>
