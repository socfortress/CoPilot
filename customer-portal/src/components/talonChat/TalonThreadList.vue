<template>
	<nav class="flex flex-col gap-2" :aria-label="$t('talonChat.threads.title')" data-testid="talon-thread-list">
		<div class="flex items-center justify-between gap-2">
			<h2 class="m-0 text-sm font-semibold">{{ $t("talonChat.threads.title") }}</h2>
			<n-button size="small" type="primary" secondary :disabled="busy" data-testid="talon-thread-new" @click="emit('new')">
				<template #icon><Icon name="carbon:add" /></template>
				{{ $t("talonChat.threads.new") }}
			</n-button>
		</div>

		<n-alert v-if="errorCode" type="warning" :bordered="false" data-testid="talon-thread-list-error">
			<div class="flex flex-wrap items-center justify-between gap-3">
				<span>{{ $t("talonChat.threads.loadFailed") }}</span>
				<n-button size="small" secondary @click="emit('retry')">{{ $t("common.actions.tryAgain") }}</n-button>
			</div>
		</n-alert>

		<p v-else-if="!loading && !threads.length" class="text-secondary m-0 text-sm" data-testid="talon-thread-list-empty">
			{{ $t("talonChat.threads.empty") }}
		</p>

		<ul class="m-0 flex list-none flex-col gap-1 p-0">
			<li v-for="thread of threads" :key="thread.id" class="group flex items-center gap-1">
				<button
					type="button"
					class="hover:bg-hover flex min-w-0 grow flex-col items-start gap-0.5 rounded-md border-0 bg-transparent px-2 py-1.5 text-left"
					:class="{ 'bg-secondary': thread.id === selectedId, 'opacity-60': !thread.accessible }"
					:aria-current="thread.id === selectedId ? 'true' : undefined"
					:disabled="busy && thread.id !== selectedId"
					:data-testid="`talon-thread-${thread.id}`"
					@click="emit('select', thread.id)"
				>
					<span class="w-full truncate text-sm font-medium">{{ threadTitle(thread) }}</span>
					<span class="text-secondary flex w-full flex-wrap gap-x-2 text-xs">
						<span class="truncate">{{ customerName(thread.customer_code) }}</span>
						<span v-if="thread.context_alert_id">{{ $t("talonChat.threads.aboutAlert", { id: thread.context_alert_id }) }}</span>
						<span v-if="!thread.accessible" data-testid="talon-thread-not-accessible">{{ $t("talonChat.threads.notAccessible") }}</span>
					</span>
				</button>
				<n-popconfirm
					:positive-text="$t('talonChat.threads.archive')"
					:negative-text="$t('common.actions.cancel')"
					@positive-click="emit('archive', thread.id)"
				>
					<template #trigger>
						<n-button
							size="tiny"
							quaternary
							:aria-label="$t('talonChat.threads.archiveNamed', { title: threadTitle(thread) })"
							:title="$t('talonChat.threads.archiveNamed', { title: threadTitle(thread) })"
							:disabled="busy && thread.id === selectedId"
							:data-testid="`talon-thread-archive-${thread.id}`"
						>
							<template #icon><Icon name="carbon:close" /></template>
						</n-button>
					</template>
					{{ $t("talonChat.threads.archiveConfirm") }}
				</n-popconfirm>
			</li>
		</ul>

		<div v-if="loading" class="flex justify-center py-2"><n-spin size="small" /></div>
		<n-button v-else-if="hasMore" size="small" quaternary data-testid="talon-thread-more" @click="emit('more')">
			{{ $t("talonChat.threads.loadMore") }}
		</n-button>
	</nav>
</template>

<script setup lang="ts">
import type { TalonChatThread } from "@/types/talonChat"
import { NAlert, NButton, NPopconfirm, NSpin } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { useCustomers } from "@/composables/common/useCustomers"
import { threadTitle } from "./talonChat"

/** The user's open "Ask Talon" conversations, newest activity first. */
const {
	threads,
	selectedId = null,
	loading = false,
	hasMore = false,
	errorCode = null,
	busy = false
} = defineProps<{
	threads: TalonChatThread[]
	selectedId?: string | null
	loading?: boolean
	hasMore?: boolean
	errorCode?: string | null
	/** A reply is streaming in the open conversation: it may not be left or closed until it ends. */
	busy?: boolean
}>()

const emit = defineEmits<{ select: [id: string]; archive: [id: string]; new: []; more: []; retry: [] }>()

const { customerName } = useCustomers()
</script>
