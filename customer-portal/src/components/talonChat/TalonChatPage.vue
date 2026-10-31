<template>
	<div class="flex flex-col gap-6" data-testid="talon-chat-page">
		<header class="flex flex-col gap-1.5">
			<h1 class="font-display text-2xl leading-tight font-semibold tracking-tight">{{ $t("talonChat.page.title") }}</h1>
			<p class="text-secondary m-0 text-sm">{{ $t("talonChat.page.intro") }}</p>
			<!-- Said on every visit: what Talon can't do, and who may read the chats (talon-analyst D97 Q7). -->
			<ul class="text-secondary m-0 flex list-none flex-col gap-1 p-0 text-xs" data-testid="talon-chat-notices">
				<li class="flex items-center gap-2" data-testid="talon-chat-no-actions">
					<Icon name="carbon:information" :size="14" class="shrink-0" />{{ $t("talonChat.page.noActionsNotice") }}
				</li>
				<li class="flex items-center gap-2" data-testid="talon-chat-review-notice">
					<Icon name="carbon:view" :size="14" class="shrink-0" />{{ $t("talonChat.page.reviewNotice") }}
				</li>
			</ul>
		</header>

		<div v-if="checking" class="flex justify-center py-10"><n-spin /></div>

		<div
			v-else-if="!enabled"
			class="bg-default border-default flex flex-col items-center gap-2 rounded-lg border px-6 py-14 text-center"
			data-testid="talon-chat-unavailable"
		>
			<Icon name="carbon:chat-bot" :size="28" class="text-tertiary" />
			<p class="m-0 font-semibold">{{ $t("talonChat.page.unavailableTitle") }}</p>
			<p class="text-secondary m-0 max-w-md text-sm">{{ $t("talonChat.page.unavailableText") }}</p>
		</div>

		<div v-else class="grid grid-cols-1 gap-6 lg:grid-cols-[18rem_minmax(0,1fr)]">
			<TalonThreadList
				:threads
				:selected-id
				:loading="loadingThreads"
				:has-more="!!nextCursor"
				:error-code="threadsErrorCode"
				@select="select"
				@archive="archive"
				@new="startNew"
				@more="loadThreads(true)"
				@retry="loadThreads()"
			/>

			<section class="min-w-0">
				<TalonNewThread
					v-if="showNew || !selectedId"
					:customers="chatCustomers"
					:cancellable="!!selectedId"
					@created="created"
					@cancel="showNew = false"
				/>
				<TalonConversation v-else :thread-id="selectedId" @turn="loadThreads(false, true)" />
			</section>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { PortalCustomer } from "@/types/auth"
import type { TalonChatThread } from "@/types/talonChat"
import { NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import { useI18n } from "vue-i18n"
import { useRoute, useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { useTalonChatAvailability } from "@/composables/common/useTalonChatAvailability"
import { useAuthStore } from "@/stores/auth"
import { errorCodeOf, errorText } from "./talonChat"
import TalonConversation from "./TalonConversation.vue"
import TalonNewThread from "./TalonNewThread.vue"
import TalonThreadList from "./TalonThreadList.vue"

/**
 * "Ask Talon" (talon-analyst D97): the user's conversations with Talon, one organization each.
 * Shown only when the availability route says Ask Talon is on; CoPilot and talon-analyst check
 * the switch again on every request. The open conversation is in the address (`?thread=`).
 */
const route = useRoute()
const router = useRouter()
const toast = useMessage()
const { t } = useI18n()
const authStore = useAuthStore()
const { isEnabledFor, availabilityFor } = useTalonChatAvailability()

const PAGE_SIZE = 20

const checking = ref(true)
const enabled = ref(false)
const chatCustomers = ref<PortalCustomer[]>([])

const threads = ref<TalonChatThread[]>([])
const nextCursor = ref<string | null>(null)
const threadsErrorCode = ref<string | null>(null)
const { loading: loadingThreads, run } = useLatestRequest()
const showNew = ref(false)

const selectedId = computed(() => {
	const value = route.query.thread
	return typeof value === "string" && value ? value : null
})

async function checkAvailability() {
	const customers = authStore.accessibleCustomers
	const [any, ...each] = await Promise.all([
		isEnabledFor(),
		...customers.map(customer => availabilityFor(customer.customer_code))
	])
	chatCustomers.value = customers.filter((_, index) => !!each[index])
	enabled.value = any || chatCustomers.value.length > 0
	checking.value = false
}

/** Load the first page; `more` the next one; `quiet` refreshes without a spinner. */
function loadThreads(more = false, quiet = false) {
	threadsErrorCode.value = null
	const cursor = more ? nextCursor.value : null
	return run(
		async signal => {
			const res = await Api.talonChat.listThreads({ status: "active", limit: PAGE_SIZE, cursor }, signal)
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
	showNew.value = false
	if (id !== selectedId.value) router.push({ query: { ...route.query, thread: id } })
}

function startNew() {
	showNew.value = true
}

function created(thread: TalonChatThread) {
	threads.value = [thread, ...threads.value.filter(item => item.id !== thread.id)]
	select(thread.id)
}

async function archive(id: string) {
	try {
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
