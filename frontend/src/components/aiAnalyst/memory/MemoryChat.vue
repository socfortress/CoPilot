<template>
	<div class="flex flex-col gap-3" data-testid="talon-memory-chat">
		<p class="text-secondary text-sm">
			What Talon remembers from your own chats (your preferences and notes), used only in your conversations.
			Nobody else sees it, admins included.
		</p>
		<MemoryProblem v-if="problem" :state="problem" @retry="load()" />
		<div v-else-if="loading && !items.length" class="flex justify-center py-8"><n-spin size="small" /></div>
		<n-empty
			v-else-if="!items.length"
			description="Talon remembers nothing from your chats yet"
			class="py-8"
			data-testid="talon-memory-chat-empty"
		/>
		<n-alert v-if="forgetFailure" type="error" :bordered="false" data-testid="talon-memory-chat-error">
			<bdi>{{ forgetFailure }}</bdi>
		</n-alert>
		<ul
			v-if="items.length"
			class="border-default flex list-none flex-col divide-y rounded-lg border p-0"
			aria-label="Your chat memory"
		>
			<li
				v-for="row of items"
				:key="row.drawer_id"
				class="border-default flex items-start justify-between gap-3 px-3 py-2"
				data-testid="talon-memory-chat-item"
				:data-drawer="row.drawer_id"
			>
				<div class="flex min-w-0 flex-col gap-0.5">
					<span class="text-sm break-words">
						<bdi>{{ row.preview ?? "(no preview)" }}</bdi>
					</span>
					<span class="text-tertiary text-xs">{{ formatTime(row.filed_at) }}</span>
				</div>
				<n-button
					v-if="row.openable"
					size="tiny"
					secondary
					type="error"
					:aria-label="`Forget: ${row.preview ?? row.drawer_id}`"
					data-testid="talon-memory-chat-forget"
					@click="pending = row"
				>
					Forget…
				</n-button>
			</li>
		</ul>

		<n-modal
			:show="pending !== null"
			preset="card"
			title="Forget this from your chat memory?"
			:style="{ maxWidth: 'min(480px, 94vw)' }"
			:mask-closable="!forgetting"
			:closable="!forgetting"
			segmented
			data-testid="talon-memory-chat-confirm"
			@update:show="value => !value && !forgetting && (pending = null)"
		>
			<p v-if="pending" class="text-sm">
				Talon will stop recalling “
				<bdi>{{ pending.preview ?? pending.drawer_id }}</bdi>
				” in your chats. This can't be undone, and the forget is recorded in the audit log.
			</p>
			<template #footer>
				<div class="flex justify-end gap-2">
					<n-button :disabled="forgetting" data-testid="talon-memory-chat-cancel" @click="pending = null">
						Cancel
					</n-button>
					<n-button
						type="error"
						:loading="forgetting"
						:disabled="forgetting"
						data-testid="talon-memory-chat-confirm-button"
						@click="forget()"
					>
						Forget
					</n-button>
				</div>
			</template>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
// "My chat memory": the signed-in user's own chat memory (decision 2: each user sees only their
// own; CoPilot uses the session's user id, never one from the page), each item with a confirmed,
// audited Forget.
import type { TalonMemoryFailure } from "@/api/endpoints/talonMemory"
import type { TalonChatMemoryItem } from "@/types/talonMemory"
import { NAlert, NButton, NEmpty, NModal, NSpin } from "naive-ui"
import { computed, onBeforeUnmount, onMounted, ref } from "vue"
import Api from "@/api"
import { memoryFailure } from "@/api/endpoints/talonMemory"
import { formatTime } from "../health/health"
import { problemState } from "./memory"
import MemoryProblem from "./MemoryProblem.vue"

const items = ref<TalonChatMemoryItem[]>([])
const failure = ref<TalonMemoryFailure | null>(null)
const loading = ref(false)
const pending = ref<TalonChatMemoryItem | null>(null)
const forgetting = ref(false)
const forgetFailure = ref<string | null>(null)
let controller: AbortController | null = null

const problem = computed(() => problemState(failure.value))

async function load() {
	controller?.abort()
	const own = new AbortController()
	controller = own
	loading.value = true
	failure.value = null
	try {
		const { data } = await Api.talonMemory.listMyChatMemory(own.signal)
		if (controller !== own) return
		items.value = data.items ?? []
	} catch (err) {
		if (controller !== own || own.signal.aborted) return
		items.value = []
		failure.value = memoryFailure(err)
	} finally {
		if (controller === own) loading.value = false
	}
}

async function forget() {
	const row = pending.value
	if (!row || forgetting.value) return
	forgetting.value = true
	forgetFailure.value = null
	try {
		await Api.talonMemory.forgetMyChatMemory(row.drawer_id)
		items.value = items.value.filter(i => i.drawer_id !== row.drawer_id)
	} catch (err) {
		const why = memoryFailure(err)
		if (why.code === "not_found") {
			items.value = items.value.filter(i => i.drawer_id !== row.drawer_id)
			forgetFailure.value = "Talon no longer had that memory."
		} else {
			forgetFailure.value = why.detail
		}
	} finally {
		forgetting.value = false
		pending.value = null
	}
}

onMounted(load)
onBeforeUnmount(() => controller?.abort())
</script>
