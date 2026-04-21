<template>
	<div class="flex h-full flex-col overflow-hidden">
		<n-scrollbar ref="scrollbar" class="grow">
			<div v-if="messages.length" class="flex flex-col gap-6 p-4 pb-20">
				<TalonChatBubble v-for="msg of messages" :key="msg.id" :msg />

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
import { nextTick, ref } from "vue"
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

let abortController: AbortController | null = null

function useExample(example: string) {
	input.value = example
	sendMessage({ input: example })
}

function clearChat() {
	messages.value = []
}

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
	clearHistory() {
		messages.value = []
	}
})
</script>
