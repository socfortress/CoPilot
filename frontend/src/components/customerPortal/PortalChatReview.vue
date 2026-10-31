<template>
	<div class="flex flex-col gap-3" data-testid="portal-chat-review">
		<p class="text-secondary m-0 text-xs">
			Read-only. Every transcript you open is recorded in Talon's audit log. The conversations are the customer's
			own: their text and Talon's answers are shown as written, never as links or formatting.
		</p>

		<n-alert v-if="refusal" type="warning" :bordered="false" data-testid="portal-chat-review-refused">
			{{ refusal }}
		</n-alert>

		<div v-else class="flex flex-col gap-3 md:flex-row">
			<div class="flex flex-col gap-2 md:w-80 md:shrink-0">
				<n-radio-group v-model:value="status" size="small" data-testid="portal-chat-review-status">
					<n-radio-button value="active">Active</n-radio-button>
					<n-radio-button value="archived">Archived</n-radio-button>
					<n-radio-button value="all">All</n-radio-button>
				</n-radio-group>

				<n-spin :show="loadingThreads">
					<div class="flex max-h-[60vh] flex-col gap-1 overflow-y-auto">
						<div
							v-if="!loadingThreads && !threads.length"
							class="text-secondary py-4 text-center text-sm"
							data-testid="portal-chat-review-empty"
						>
							No portal chats.
						</div>
						<button
							v-for="thread of threads"
							:key="thread.id"
							type="button"
							class="border-default hover:bg-secondary flex flex-col gap-0.5 rounded-md border px-3 py-2 text-left"
							:class="{ 'border-primary': thread.id === selectedId }"
							data-testid="portal-chat-review-thread"
							@click="select(thread.id)"
						>
							<span class="truncate text-sm font-medium">
								<bdi>{{ thread.title || "Untitled conversation" }}</bdi>
							</span>
							<span class="text-secondary text-xs">
								{{ threadMeta(thread) }}
							</span>
						</button>
						<n-button v-if="threadsNext" size="small" text type="primary" @click="loadThreads(true)">
							Load more
						</n-button>
					</div>
				</n-spin>
			</div>

			<div class="min-w-0 flex-1">
				<div v-if="!selectedId" class="text-secondary py-8 text-center text-sm">Pick a conversation.</div>
				<n-spin v-else :show="loadingMessages">
					<div class="flex flex-col gap-3" data-testid="portal-chat-review-transcript">
						<n-alert v-if="messagesRefusal" type="warning" :bordered="false">{{ messagesRefusal }}</n-alert>
						<n-button v-if="messagesNext" size="small" text type="primary" @click="loadMessages(true)">
							Load earlier turns
						</n-button>
						<div
							v-for="turn of turns"
							:key="turn.id"
							class="border-default flex flex-col gap-1 rounded-md border px-3 py-2"
							:data-who="turn.who"
							data-testid="portal-chat-review-turn"
						>
							<div class="text-secondary flex flex-wrap items-center gap-2 text-xs">
								<span class="font-semibold">{{ WHO[turn.who] }}</span>
								<span v-if="turn.createdAt">{{ formatDate(turn.createdAt, dFormats.datetime) }}</span>
								<span v-if="turn.status && turn.status !== 'completed'">({{ turn.status }})</span>
								<span v-if="turn.feedback" data-testid="portal-chat-review-feedback">
									{{
										turn.feedback === "up"
											? "Customer rated it helpful"
											: "Customer rated it unhelpful"
									}}
								</span>
							</div>
							<template v-for="(line, index) of turn.lines" :key="index">
								<p v-if="line.kind === 'text'" class="m-0 text-sm whitespace-pre-wrap">
									<bdi>{{ line.text }}</bdi>
								</p>
								<p v-else class="text-secondary m-0 text-xs" :data-kind="line.kind">
									<bdi>{{ line.text }}</bdi>
								</p>
							</template>
							<p v-if="turn.errorText" class="text-error m-0 text-xs">
								<bdi>{{ turn.errorText }}</bdi>
							</p>
						</div>
					</div>
				</n-spin>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ReviewTurn } from "./portalChat"
import type { ApiError } from "@/types/common"
import type { TalonPortalReviewThread } from "@/types/talonPortalReview"
import type { TalonV2UIMessage } from "@/types/talonV2"
import { NAlert, NButton, NRadioButton, NRadioGroup, NSpin } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import { reviewTurns } from "./portalChat"

const { customerCode } = defineProps<{ customerCode: string }>()

const WHO: Record<ReviewTurn["who"], string> = { customer: "Customer", talon: "Talon", other: "Other" }
/** The review's fixed refusal texts, by code; anything else is the fixed fallback. */
const REFUSALS: Record<string, string> = {
	review_forbidden:
		"You can't review this customer's portal chats: it takes an admin, or an analyst or responder with this customer and access to all of its alert tags.",
	thread_not_found: "This conversation can't be shown to you.",
	invalid_request: "The request was refused."
}
const FALLBACK = "Portal chats can't be read right now."

const dFormats = useSettingsStore().dateFormat
const status = ref<"active" | "archived" | "all">("all")
const threads = ref<TalonPortalReviewThread[]>([])
const threadsNext = ref<string | null>(null)
const loadingThreads = ref(false)
const refusal = ref<string | null>(null)

const selectedId = ref<string | null>(null)
const messages = ref<TalonV2UIMessage[]>([])
const messagesNext = ref<string | null>(null)
const loadingMessages = ref(false)
const messagesRefusal = ref<string | null>(null)
const turns = computed(() => reviewTurns(messages.value))

function refusalText(err: unknown): string {
	const data = (err as ApiError)?.response?.data as { code?: unknown } | undefined
	const code = typeof data?.code === "string" ? data.code : null
	if ((err as ApiError)?.response?.status === 404 && !code) return "Talon v2 is off: portal chats can't be reviewed."
	return (code && REFUSALS[code]) || FALLBACK
}

function threadMeta(thread: TalonPortalReviewThread): string {
	const parts: string[] = []
	if (thread.user_id !== undefined && thread.user_id !== null) parts.push(`user ${thread.user_id}`)
	if (typeof thread.turns === "number") parts.push(`${thread.turns} turn${thread.turns === 1 ? "" : "s"}`)
	const up = thread.feedback?.up ?? 0
	const down = thread.feedback?.down ?? 0
	if (up || down) parts.push(`${up} up, ${down} down`)
	if (thread.updated_at) parts.push(String(formatDate(thread.updated_at, dFormats.datetime)))
	if (thread.status && thread.status !== "active") parts.push(thread.status)
	return parts.join(" · ")
}

function loadThreads(more = false) {
	loadingThreads.value = true
	Api.talonPortalReview
		.listThreads(customerCode, { status: status.value, cursor: more ? threadsNext.value : null })
		.then(res => {
			refusal.value = null
			const page = Array.isArray(res.data?.threads) ? res.data.threads : []
			threads.value = more ? [...threads.value, ...page] : page
			threadsNext.value = typeof res.data?.next === "string" ? res.data.next : null
		})
		.catch(err => {
			refusal.value = refusalText(err)
		})
		.finally(() => {
			loadingThreads.value = false
		})
}

function loadMessages(older = false) {
	if (!selectedId.value) return
	const threadId = selectedId.value
	loadingMessages.value = true
	Api.talonPortalReview
		.getMessages(threadId, { before: older ? messagesNext.value : null })
		.then(res => {
			if (selectedId.value !== threadId) return
			messagesRefusal.value = null
			const page = Array.isArray(res.data?.messages) ? res.data.messages : []
			messages.value = older ? [...page, ...messages.value] : page
			messagesNext.value = typeof res.data?.next === "string" ? res.data.next : null
		})
		.catch(err => {
			if (selectedId.value === threadId) messagesRefusal.value = refusalText(err)
		})
		.finally(() => {
			loadingMessages.value = false
		})
}

function select(threadId: string) {
	selectedId.value = threadId
	messages.value = []
	messagesNext.value = null
	loadMessages()
}

watch(status, () => {
	selectedId.value = null
	loadThreads()
})

onBeforeMount(() => loadThreads())
</script>
