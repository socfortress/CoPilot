<template>
	<div class="flex flex-col gap-6" data-testid="talon-chat-page">
		<!-- On: the inbox names itself ("Conversations") and the breadcrumb says "Ask Talon"; the page title stays for screen readers. -->
		<header v-if="!enabled" class="flex flex-col gap-1.5">
			<h1 class="font-display text-2xl leading-tight font-semibold tracking-tight">{{ $t("talonChat.page.title") }}</h1>
			<p class="text-secondary m-0 text-sm">{{ $t("talonChat.page.intro") }}</p>
		</header>
		<h1 v-else class="sr-only">{{ $t("talonChat.page.title") }}</h1>

		<div v-if="checking" class="flex justify-center py-10"><n-spin /></div>

		<div
			v-else-if="!enabled && checkFailed"
			class="bg-default border-default flex flex-col items-center gap-2 rounded-lg border px-6 py-14 text-center"
			data-testid="talon-chat-check-failed"
		>
			<Icon name="carbon:warning" :size="28" class="text-tertiary" />
			<p class="m-0 font-semibold">{{ $t("talonChat.page.checkFailedTitle") }}</p>
			<p class="text-secondary m-0 max-w-md text-sm">{{ $t("talonChat.page.checkFailedText") }}</p>
			<n-button size="small" secondary data-testid="talon-chat-check-retry" @click="refresh()">
				{{ $t("common.actions.tryAgain") }}
			</n-button>
		</div>

		<div
			v-else-if="!enabled"
			class="bg-default border-default flex flex-col items-center gap-2 rounded-lg border px-6 py-14 text-center"
			data-testid="talon-chat-unavailable"
		>
			<Icon name="carbon:chat-bot" :size="28" class="text-tertiary" />
			<p class="m-0 font-semibold">{{ $t("talonChat.page.unavailableTitle") }}</p>
			<p class="text-secondary m-0 max-w-md text-sm">{{ $t("talonChat.page.unavailableText") }}</p>
		</div>

		<div v-else class="inbox" :class="{ 'has-detail': detailOpen }" data-testid="talon-inbox">
			<TalonThreadList
				class="inbox-list"
				:threads
				:selected-id
				:filter
				:loading="loadingThreads"
				:has-more="!!nextCursor"
				:error-code="threadsErrorCode"
				:busy="streaming"
				@select="select"
				@archive="archive"
				@new="startNew"
				@more="loadThreads(true)"
				@retry="loadThreads()"
				@filter="setFilter"
			/>

			<section class="inbox-pane" data-testid="talon-inbox-pane">
				<template v-if="showNew || !selectedId">
					<div v-if="detailOpen" class="border-default flex h-13 shrink-0 items-center border-b px-2 lg:hidden">
						<n-button quaternary size="small" :disabled="streaming" data-testid="talon-inbox-back" @click="back()">
							<template #icon><Icon name="carbon:arrow-left" /></template>
							{{ $t("talonChat.threads.title") }}
						</n-button>
					</div>
					<TalonNewThread :customers="chatCustomers" :cancellable="!!selectedId" @created="created" @cancel="showNew = false" />
				</template>
				<TalonConversation
					v-else
					:thread-id="selectedId"
					@turn="loadThreads(false, true)"
					@streaming="value => (streaming = value)"
					@archive="archive"
				>
					<template #leading>
						<n-button
							quaternary
							circle
							size="small"
							class="lg:hidden!"
							:disabled="streaming"
							:aria-label="$t('talonChat.threads.back')"
							data-testid="talon-inbox-back"
							@click="back()"
						>
							<template #icon><Icon name="carbon:arrow-left" /></template>
						</n-button>
					</template>
				</TalonConversation>

				<!-- Said on every visit: what Talon can't do, and who may read the chats (talon-analyst D97 Q7). -->
				<ul class="notices" data-testid="talon-chat-notices">
					<li data-testid="talon-chat-no-actions">
						<Icon name="carbon:information" :size="13" class="shrink-0" />{{ $t("talonChat.page.noActionsNotice") }}
					</li>
					<li data-testid="talon-chat-review-notice">
						<Icon name="carbon:view" :size="13" class="shrink-0" />{{ $t("talonChat.page.reviewNotice") }}
					</li>
				</ul>
			</section>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { PortalCustomer } from "@/types/auth"
import type { TalonChatThread, TalonChatThreadStatusFilter } from "@/types/talonChat"
import { NButton, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import { useI18n } from "vue-i18n"
import { useRoute, useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { useTalonChatAvailability } from "@/composables/common/useTalonChatAvailability"
import { useAuthStore } from "@/stores/auth"
import { errorCodeOf, errorText, THREAD_ID } from "./talonChat"
import TalonConversation from "./TalonConversation.vue"
import TalonNewThread from "./TalonNewThread.vue"
import TalonThreadList from "./TalonThreadList.vue"

/**
 * "Ask Talon" (talon-analyst D97): the user's conversations with Talon, one organization each.
 * Shown only when the availability route says Ask Talon is on; CoPilot and talon-analyst check
 * the switch again on every request. The open conversation is in the address (`?thread=`).
 *
 * Laid out as an inbox (the restyle's variant 07): the conversations beside the open one, in a panel
 * the height of the window, so the composer stays in view. Below `lg` it is one or the other.
 */
const route = useRoute()
const router = useRouter()
const toast = useMessage()
const { t } = useI18n()
const authStore = useAuthStore()
const { lookup } = useTalonChatAvailability()

const PAGE_SIZE = 20

const checking = ref(true)
const enabled = ref(false)
/** No organization could be confirmed on, and a lookup failed: "couldn't check", not "off". */
const checkFailed = ref(false)
/** A reply is streaming: nothing may replace the conversation until it ends. */
const streaming = ref(false)
const chatCustomers = ref<PortalCustomer[]>([])

const threads = ref<TalonChatThread[]>([])
const nextCursor = ref<string | null>(null)
const threadsErrorCode = ref<string | null>(null)
const { loading: loadingThreads, run } = useLatestRequest()
const showNew = ref(false)
/** Open or archived conversations; an archived one opens read only. */
const filter = ref<Extract<TalonChatThreadStatusFilter, "active" | "archived">>("active")

const selectedId = computed(() => {
	// Only a well-formed id is read from the address; anything else opens no conversation.
	const value = route.query.thread
	return typeof value === "string" && THREAD_ID.test(value) ? value : null
})
/** Narrow screens show the list or this: a conversation, or the new one being started. */
const detailOpen = computed(() => showNew.value || !!selectedId.value)

async function checkAvailability() {
	const customers = authStore.accessibleCustomers
	const [any, ...each] = await Promise.all([lookup(), ...customers.map(customer => lookup(customer.customer_code))])
	chatCustomers.value = customers.filter((_, index) => each[index]?.state === "on")
	enabled.value = any?.state === "on" || chatCustomers.value.length > 0
	checkFailed.value = !enabled.value && [any, ...each].some(answer => answer?.state === "error")
	checking.value = false
}

/** Load the first page; `more` the next one; `quiet` refreshes without a spinner. */
function loadThreads(more = false, quiet = false) {
	threadsErrorCode.value = null
	const cursor = more ? nextCursor.value : null
	return run(
		async signal => {
			const res = await Api.talonChat.listThreads({ status: filter.value, limit: PAGE_SIZE, cursor }, signal)
			const page = res.data.threads ?? []
			if (more) {
				const shown = new Set(threads.value.map(thread => thread.id))
				threads.value = [...threads.value, ...page.filter(thread => !shown.has(thread.id))]
			} else {
				threads.value = page
			}
			nextCursor.value = res.data.next ?? null
		},
		err => {
			if (!quiet) threadsErrorCode.value = errorCodeOf(err) ?? "unknown"
		}
	)
}

function select(id: string) {
	if (streaming.value) return
	showNew.value = false
	if (id !== selectedId.value) router.push({ query: { ...route.query, thread: id } })
}

function setFilter(value: typeof filter.value) {
	filter.value = value
	threads.value = []
	nextCursor.value = null
	loadThreads()
}

/** Back to the list on a narrow screen: the conversation leaves the address. */
function back() {
	if (streaming.value) return
	showNew.value = false
	if (selectedId.value) {
		const { thread: _closed, ...query } = route.query
		router.replace({ query })
	}
}

function startNew() {
	if (streaming.value) return
	showNew.value = true
}

function created(thread: TalonChatThread) {
	// A new conversation is an open one: the list shows those again if it was on the archived.
	if (filter.value !== "active") setFilter("active")
	threads.value = [thread, ...threads.value.filter(item => item.id !== thread.id)]
	select(thread.id)
}

async function archive(id: string) {
	if (streaming.value && id === selectedId.value) return
	try {
		// The answer is the thread `archived`, or `deleted` when it had no turn: gone from the list either way.
		await Api.talonChat.archiveThread(id)
		threads.value = threads.value.filter(thread => thread.id !== id)
		toast.success(t("talonChat.threads.archived"))
		if (selectedId.value === id) {
			const { thread: _closed, ...query } = route.query
			router.replace({ query })
		}
	} catch (err) {
		toast.error(errorText(errorCodeOf(err)))
	}
}

async function refresh() {
	const wasEnabled = enabled.value
	await checkAvailability()
	if (enabled.value && !wasEnabled) await loadThreads()
}

// The profile names the user's customers after the token did: read again when they change.
watch(
	() => authStore.accessibleCustomerCodes.join(","),
	() => refresh()
)

onBeforeMount(refresh)
</script>

<style scoped>
.inbox {
	display: grid;
	grid-template-columns: minmax(0, 1fr);
	/* The page's own bottom padding (`--view-padding`) is the gap under it: nothing left to scroll. */
	height: calc(100svh - var(--header-bar-height) - var(--toolbar-height) - var(--view-padding));
	min-height: 32rem;
	overflow: hidden;
	border: 1px solid var(--border-color);
	border-radius: 12px;
	background: var(--bg-body-color);
}
.inbox-list,
.inbox-pane {
	min-height: 0;
}
.inbox-pane {
	display: flex;
	flex-direction: column;
}
.notices {
	display: flex;
	flex-shrink: 0;
	flex-wrap: wrap;
	gap: 4px 16px;
	margin: 0;
	padding: 0 20px 12px;
	list-style: none;
	color: var(--fg-tertiary-color);
	font-size: 11px;
	line-height: 16px;
}
.notices li {
	display: flex;
	align-items: center;
	gap: 6px;
}

@media (min-width: 1024px) {
	.inbox {
		grid-template-columns: 26rem minmax(0, 1fr);
	}
	.inbox-list {
		border-right: 1px solid var(--border-color);
	}
}
@media (max-width: 1023px) {
	.inbox.has-detail .inbox-list,
	.inbox:not(.has-detail) .inbox-pane {
		display: none;
	}
}
/* No header bar on a phone: the panel starts under the toolbar. */
@media (max-width: 700px) {
	.inbox {
		height: calc(100svh - var(--toolbar-height) - var(--view-padding));
		min-height: 28rem;
	}
}
</style>
