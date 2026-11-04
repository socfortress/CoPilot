<template>
	<nav class="relative flex min-h-0 flex-col" :aria-label="$t('talonChat.threads.title')" data-testid="talon-thread-list">
		<div class="flex flex-col gap-3 px-4 pt-4 pb-3">
			<div class="flex items-center justify-between gap-2">
				<h2 class="font-display m-0 text-xl leading-tight font-semibold tracking-tight">{{ $t("talonChat.threads.title") }}</h2>
				<n-button size="small" type="primary" secondary class="max-lg:hidden!" :disabled="busy" data-testid="talon-thread-new" @click="emit('new')">
					<template #icon><Icon name="carbon:add" /></template>
					{{ $t("talonChat.threads.new") }}
				</n-button>
			</div>

			<n-input
				v-model:value="query"
				size="small"
				clearable
				:placeholder="$t('talonChat.threads.search')"
				:disabled="!threads.length"
				:input-props="{ 'aria-label': $t('talonChat.threads.search') }"
				data-testid="talon-thread-search"
			>
				<template #prefix><Icon name="carbon:search" /></template>
			</n-input>

			<n-tabs
				type="segment"
				size="small"
				:value="filter"
				animated
				:aria-label="$t('talonChat.threads.filterLabel')"
				data-testid="talon-thread-filter"
				@update:value="pickFilter"
			>
				<n-tab v-for="option of FILTERS" :key="option" :name="option" :data-testid="`talon-thread-filter-${option}`">
					{{ $t(`talonChat.threads.filter.${option}`) }}
				</n-tab>
			</n-tabs>
		</div>

		<div class="list-scroll border-default min-h-0 grow overflow-y-auto border-t">
			<n-alert v-if="errorCode" type="warning" :bordered="false" class="m-3" data-testid="talon-thread-list-error">
				<div class="flex flex-wrap items-center justify-between gap-3">
					<span>{{ $t("talonChat.threads.loadFailed") }}</span>
					<n-button size="small" secondary @click="emit('retry')">{{ $t("common.actions.tryAgain") }}</n-button>
				</div>
			</n-alert>

			<div
				v-else-if="!loading && !threads.length"
				class="text-secondary flex flex-col items-center gap-1.5 px-6 py-14 text-center text-sm"
				data-testid="talon-thread-list-empty"
			>
				<Icon name="carbon:chat" :size="24" class="text-tertiary" />
				<template v-if="filter === 'archived'">{{ $t("talonChat.threads.emptyArchived") }}</template>
				<template v-else>
					<strong class="text-default font-semibold">{{ $t("talonChat.threads.empty") }}</strong>
					<span>{{ $t("talonChat.threads.emptyHint") }}</span>
				</template>
			</div>

			<p v-else-if="!shown.length && query.trim()" class="text-secondary m-0 px-6 py-10 text-center text-sm" data-testid="talon-thread-no-match">
				{{ $t("talonChat.threads.noMatch", { query: query.trim() }) }}
			</p>

			<ul class="m-0 list-none p-0">
				<li v-for="thread of shown" :key="thread.id" class="row" :class="{ 'is-selected': thread.id === selectedId }">
					<!-- The row is one target: the button covers it (::after), the actions sit above it. -->
					<button
						type="button"
						class="row-main"
						:class="{ 'opacity-60': !thread.accessible }"
						:aria-current="thread.id === selectedId ? 'true' : undefined"
						:disabled="busy && thread.id !== selectedId"
						:data-testid="`talon-thread-${thread.id}`"
						@click="emit('select', thread.id)"
					>
						<span class="line-clamp-2 text-sm leading-5 font-semibold">{{ threadTitle(thread) }}</span>
						<span class="text-secondary flex w-full flex-wrap items-center gap-x-2 gap-y-1 text-xs">
							<span class="truncate">{{ customerName(thread.customer_code) }}</span>
							<span v-if="thread.context_alert_id" class="chip">{{ $t("talonChat.threads.aboutAlert", { id: thread.context_alert_id }) }}</span>
							<span v-if="!thread.accessible" class="chip" data-testid="talon-thread-not-accessible">
								{{ $t("talonChat.threads.notAccessible") }}
							</span>
						</span>
					</button>
					<div class="row-side">
						<time class="text-secondary text-xs leading-5 tabular-nums" :datetime="thread.updated_at" :title="fullTime(thread.updated_at)">
							{{ threadTime(thread.updated_at) }}
						</time>
						<TalonThreadActions
							v-if="thread.status === 'active'"
							:thread
							:disabled="busy && thread.id === selectedId"
							:data-testid="`talon-thread-actions-${thread.id}`"
							@archive="id => emit('archive', id)"
						/>
					</div>
				</li>
			</ul>

			<div v-if="loading" class="flex justify-center py-4"><n-spin size="small" /></div>
			<div v-else-if="hasMore" class="flex justify-center py-3">
				<n-button size="small" quaternary data-testid="talon-thread-more" @click="emit('more')">
					{{ $t("talonChat.threads.loadMore") }}
				</n-button>
			</div>
		</div>

		<!-- On a narrow screen the list is a page of its own: New floats over it. -->
		<n-button
			type="primary"
			class="fab lg:hidden!"
			:disabled="busy"
			:aria-label="$t('talonChat.threads.new')"
			data-testid="talon-thread-new-fab"
			@click="emit('new')"
		>
			<template #icon><Icon name="carbon:add" /></template>
			{{ $t("talonChat.threads.newShort") }}
		</n-button>
	</nav>
</template>

<script setup lang="ts">
import type { TalonChatThread, TalonChatThreadStatusFilter } from "@/types/talonChat"
import { NAlert, NButton, NInput, NSpin, NTab, NTabs } from "naive-ui"
import { computed, ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import { useCustomers } from "@/composables/common/useCustomers"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import { threadMatches, threadTime, threadTitle } from "./talonChat"
import TalonThreadActions from "./TalonThreadActions.vue"

/**
 * The user's "Ask Talon" conversations as an inbox, newest activity first: open or archived, a
 * search over what is loaded (titles and organizations: the API has no search of its own), and
 * each row's actions in a menu (`TalonThreadActions`).
 */
const {
	threads,
	selectedId = null,
	filter = "active",
	loading = false,
	hasMore = false,
	errorCode = null,
	busy = false
} = defineProps<{
	threads: TalonChatThread[]
	selectedId?: string | null
	/** Which conversations are listed: the open ones, or the archived ones (read only). */
	filter?: TalonChatThreadFilter
	loading?: boolean
	hasMore?: boolean
	errorCode?: string | null
	/** A reply is streaming in the open conversation: it may not be left or closed until it ends. */
	busy?: boolean
}>()

const emit = defineEmits<{
	select: [id: string]
	archive: [id: string]
	new: []
	more: []
	retry: []
	filter: [value: TalonChatThreadFilter]
}>()

type TalonChatThreadFilter = Extract<TalonChatThreadStatusFilter, "active" | "archived">
const FILTERS: TalonChatThreadFilter[] = ["active", "archived"]

const settings = useSettingsStore()
const { customerName } = useCustomers()

const query = ref("")
const shown = computed(() =>
	threads.filter(thread => threadMatches(threadTitle(thread), customerName(thread.customer_code), query.value))
)

function pickFilter(value: string | number) {
	const option = FILTERS.find(item => item === value)
	if (option && option !== filter) emit("filter", option)
}

function fullTime(iso: string) {
	return String(formatDate(iso, settings.dateFormat.datetime, { tz: true }))
}
</script>

<style scoped>
.list-scroll {
	scrollbar-color: var(--border-color) transparent;
	scrollbar-width: thin;
}
.row {
	position: relative;
	display: flex;
	align-items: flex-start;
	border-bottom: 1px solid var(--border-color);
}
.row:hover {
	background: rgba(var(--hover-color-rgb) / 0.4);
}
.row.is-selected {
	background: var(--bg-secondary-color);
}
.row.is-selected::before {
	content: "";
	position: absolute;
	inset: 0 auto 0 0;
	width: 3px;
	background: var(--primary-color);
}
.row-main {
	display: flex;
	min-width: 0;
	flex-grow: 1;
	flex-direction: column;
	align-items: flex-start;
	gap: 6px;
	padding: 12px 4px 12px 16px;
	border: 0;
	background: transparent;
	color: inherit;
	font: inherit;
	text-align: left;
	cursor: pointer;
}
/* The whole row selects the conversation: date and blank space included. */
.row-main::after {
	content: "";
	position: absolute;
	inset: 0;
}
.row-main:focus-visible {
	outline: none;
}
.row-main:focus-visible::after {
	outline: 2px solid var(--primary-color);
	outline-offset: -2px;
}
.row-main:disabled {
	cursor: not-allowed;
}
.row-side {
	display: flex;
	flex-shrink: 0;
	flex-direction: column;
	align-items: flex-end;
	gap: 4px;
	padding: 12px 12px 8px 0;
	pointer-events: none;
}
/* Above the row's button, so the menu opens instead of the conversation. */
.row-side :deep(.n-button) {
	position: relative;
	z-index: 1;
	pointer-events: auto;
}
.chip {
	display: inline-flex;
	align-items: center;
	height: 20px;
	padding: 0 8px;
	border-radius: 999px;
	background: var(--bg-secondary-color);
	box-shadow: inset 0 0 0 1px var(--border-color);
}

.fab {
	position: absolute;
	right: 16px;
	bottom: 16px;
	height: 44px;
	padding: 0 18px;
	border-radius: 14px;
	box-shadow: 0 10px 24px rgba(0, 0, 0, 0.35);
}
</style>
