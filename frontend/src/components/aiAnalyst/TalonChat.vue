<template>
	<div class="flex h-full flex-col overflow-hidden">
		<n-scrollbar ref="scrollbar" class="grow">
			<div v-if="messages.length" class="flex flex-col gap-6 p-4 pb-20">
				<div
					v-for="msg of messages"
					:key="msg.id"
					class="group flex flex-col gap-0.5"
					:class="{ 'items-end text-right': msg.sender === 'user' }"
				>
					<template v-if="msg.sender === 'server'">
						<div class="text-secondary inline-flex items-center gap-1 text-sm font-semibold">
							<span>Talon:</span>
							<div
								v-if="isCopySupported"
								class="pointer-events-none ml-1 flex items-center opacity-0 transition-opacity duration-300 group-hover:pointer-events-auto group-hover:opacity-100"
							>
								<n-tooltip>
									<template #trigger>
										<n-button size="tiny" text @click="copyText(msg.body)">
											<template #icon>
												<Icon name="carbon:copy" :size="13" />
											</template>
										</n-button>
									</template>
									<div class="text-xs">Copy</div>
								</n-tooltip>
							</div>
						</div>
						<div class="**:text-default **:text-sm [&_*:last-child]:mb-0!">
							<Markdown :source="msg.body" class="overflow-hidden" />
						</div>
					</template>

					<template v-if="msg.sender === 'user'">
						<div class="flex items-end justify-end gap-3 pl-6">
							<div
								class="bg-secondary **:text-default rounded-lg px-2 py-1 text-sm [&_*:last-child]:mb-0!"
							>
								<Markdown :source="msg.body" class="overflow-hidden" />
							</div>
						</div>
					</template>

					<div class="text-tertiary mt-1 text-xs">
						{{ formatDate(msg.datetime, dFormats.datetime) }}
					</div>
				</div>

				<div v-if="streaming" class="group flex flex-col gap-0.5">
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
			<div v-else class="text-secondary flex flex-col items-center justify-center py-12 text-center">
				<Icon name="carbon:chat-bot" :size="40" class="mb-3 opacity-50" />
				<p class="text-lg">Talon AI Assistant</p>
				<p class="mt-1 text-sm opacity-70">Ask a question to get started</p>
			</div>
		</n-scrollbar>

		<div class="border-color flex items-end gap-2 border-t p-3">
			<n-input
				v-model:value="input"
				type="textarea"
				:autosize="{ minRows: 1, maxRows: 6 }"
				placeholder="Ask Talon..."
				:disabled="streaming"
				@keydown.enter.exact.prevent="sendMessage()"
			/>
			<n-button v-if="!streaming" type="primary" :disabled="!input?.trim()" @click="sendMessage()">
				<template #icon>
					<Icon name="carbon:send-filled" :size="16" />
				</template>
			</n-button>
			<n-button v-else type="error" @click="stopStream()">
				<template #icon>
					<Icon name="carbon:stop-filled" :size="16" />
				</template>
			</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ScrollbarInst } from "naive-ui"
import { useClipboard, useStorage } from "@vueuse/core"
import { NButton, NInput, NScrollbar, NTooltip, useMessage } from "naive-ui"
import { nanoid } from "nanoid"
import { nextTick, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import Markdown from "@/components/common/Markdown.vue"
import { useSettingsStore } from "@/stores/settings"
import { secureLocalStorage } from "@/utils/secure-storage"
import { formatDate } from "@/utils/format"

interface TalonMessage {
	id: string
	datetime: Date
	body: string
	sender: "user" | "server"
}

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const { copy: copyText, isSupported: isCopySupported } = useClipboard()

const messages = useStorage<TalonMessage[]>("talon-chat-messages", [], secureLocalStorage({ session: true }))
const input = ref("")
const streaming = ref(false)
const streamBuffer = ref("")
const scrollbar = ref<ScrollbarInst | null>(null)

let abortController: AbortController | null = null

function scrollChat() {
	nextTick(() => {
		scrollbar.value?.scrollTo({ top: 99999999999999, behavior: "smooth" })
	})
}

async function sendMessage() {
	const text = input.value?.trim()
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
