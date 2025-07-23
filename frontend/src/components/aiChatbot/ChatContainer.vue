<template>
	<div class="flex flex-col overflow-hidden">
		<div class="relative grow overflow-hidden">
			<n-scrollbar ref="scrollbar">
				<div v-if="list.length" class="pb-50 flex flex-col gap-6 p-4">
					<ChatBubbleBlock
						v-for="item of list"
						:key="item.id"
						class="animate-fade"
						:entity="item"
						@update="scrollChat()"
					/>
					<div v-if="loading" class="animate-fade">
						<Icon name="svg-spinners:pulse-rings-3" :size="20" />
					</div>
				</div>
				<div v-else class="text-secondary flex flex-col items-center justify-center py-12 text-center">
					<p class="text-lg">
						Your chat is empty.
						<br />
						Ask your first question!
					</p>
				</div>
			</n-scrollbar>
			<CollapseKeepAlive :show="!input && options.showQuestions && !!server" class="absolute! bottom-0">
				<ChatQuestions v-if="server" :server @select="input = $event" />
			</CollapseKeepAlive>
		</div>
		<div class="flex flex-col">
			<ChatQuery
				v-model:input="input"
				:loading
				@update-options="options = $event"
				@message="sendQuery"
				@select-server="server = $event"
				@server-loaded="serverLoadedHandler()"
				@stop="stopQuery()"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { RemovableRef } from "@vueuse/core"
import type { ScrollbarInst } from "naive-ui"
import type { ChatBubble } from "./ChatBubble.vue"
import type { Message } from "./ChatQuery.vue"
import { useStorage } from "@vueuse/core"
import axios from "axios"
import { NScrollbar, useMessage } from "naive-ui"
import { nanoid } from "nanoid"
import { nextTick, onBeforeMount, onMounted, ref } from "vue"
import Api from "@/api"
import CollapseKeepAlive from "@/components/common/CollapseKeepAlive.vue"
import Icon from "@/components/common/Icon.vue"
import { secureLocalStorage } from "@/utils/secure-storage"
import ChatBubbleBlock from "./ChatBubble.vue"
import ChatQuery from "./ChatQuery.vue"
import ChatQuestions from "./ChatQuestions.vue"

const message = useMessage()

const list: RemovableRef<ChatBubble[]> = useStorage<ChatBubble[]>(
	"ai-chatbot-list-messages",
	[],
	secureLocalStorage({ session: true })
)
const loading = ref(false)
const server = ref<string | null>(null)
const input = ref<string | null>(null)
const options = ref<{ verbose: boolean; showQuestions: boolean }>({ verbose: false, showQuestions: false })
const scrollbar = ref<ScrollbarInst | null>(null)

let abortController: AbortController | null = null

function scrollChat() {
	nextTick(() => {
		scrollbar.value?.scrollTo({ top: 99999999999999, behavior: "smooth" })
	})
}

function serverLoadedHandler() {
	setTimeout(() => {
		scrollChat()
	}, 500)
}

function setAllOld() {
	list.value.forEach(o => (o.new = false))
}

function addBubble(payload: Omit<ChatBubble, "datetime" | "id">) {
	setAllOld()
	list.value.push({ ...payload, datetime: new Date(), id: nanoid(), new: true })
	scrollChat()
}

function stopQuery() {
	abortController?.abort()
}

function sendQuery(payload: Message) {
	addBubble({
		body: payload.input,
		server: payload.server,
		sender: "user"
	})

	loading.value = true

	abortController = new AbortController()

	Api.copilotMCP
		.query(
			{
				input: payload.input,
				mcp_server: payload.server,
				verbose: payload.verbose
			},
			abortController.signal
		)
		.then(res => {
			if (res.data.success) {
				addBubble({
					body: res.data.structured_result.response,
					thought: res.data.structured_result.thinking_process,
					server: payload.server,
					sender: "server"
				})
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	setAllOld()
})

onMounted(() => {
	scrollChat()
})
</script>
