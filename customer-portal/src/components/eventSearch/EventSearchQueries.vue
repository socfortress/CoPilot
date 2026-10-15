<template>
	<div class="flex items-center gap-2" data-testid="event-search-queries">
		<n-popover v-model:show="showList" trigger="click" placement="bottom-start" :show-arrow="false" class="p-0!">
			<template #trigger>
				<n-button size="small" secondary :disabled="!available" :loading data-testid="saved-queries-toggle">
					<template #icon><Icon name="carbon:bookmark" /></template>
					Queries
					<span v-if="saved.length" class="text-tertiary ml-1.5 font-mono text-xs tabular-nums">{{ saved.length }}</span>
				</n-button>
			</template>

			<div class="flex max-h-[min(70vh,32rem)] w-[min(92vw,26rem)] flex-col overflow-y-auto" data-testid="saved-queries">
				<div
					v-if="error"
					class="border-default bg-error/5 flex items-center justify-between gap-3 border-b px-3 py-2"
					data-testid="saved-queries-error"
				>
					<span class="text-error text-xs">{{ error }}</span>
					<n-button size="tiny" secondary @click="emit('retry')">Retry</n-button>
				</div>
				<section class="flex flex-col">
					<header class="bg-secondary border-default flex items-baseline justify-between border-b px-3 py-2">
						<span :class="HEAD">Saved</span>
						<span class="text-tertiary font-mono text-xs tabular-nums">{{ saved.length }}</span>
					</header>
					<p v-if="!saved.length" class="text-tertiary m-0 px-3 py-3 text-xs">
						{{ loading ? "Loading…" : "No saved query yet. Run a search, then save it with a name." }}
					</p>
					<div v-else class="divide-border flex flex-col divide-y">
						<div
							v-for="entry of saved"
							:key="entry.id"
							class="group hover:bg-secondary/50 flex items-start gap-2 px-3 py-2"
							data-testid="saved-query"
						>
							<button
								type="button"
								class="flex min-w-0 grow cursor-pointer flex-col gap-0.5 text-left"
								:title="`Run “${entry.name}”`"
								@click="pick(entry)"
							>
								<span class="text-default truncate text-sm font-medium">{{ entry.name }}</span>
								<span class="text-secondary truncate font-mono text-xs [font-variant-ligatures:none]">{{ entry.query || "*" }}</span>
								<span class="text-tertiary truncate text-xs">{{ entry.source_name }} · {{ timeLabel(entry) }}</span>
							</button>
							<n-button
								size="tiny"
								quaternary
								class="opacity-60 group-hover:opacity-100"
								:aria-label="`Delete “${entry.name}”`"
								data-testid="saved-query-delete"
								@click="emit('delete', entry.id)"
							>
								<template #icon><Icon name="carbon:trash-can" :size="14" /></template>
							</n-button>
						</div>
					</div>
				</section>

				<section class="border-default flex flex-col border-t">
					<header class="bg-secondary border-default flex items-baseline justify-between border-b px-3 py-2">
						<span :class="HEAD">Recent</span>
						<n-button v-if="recent.length" text size="tiny" data-testid="recent-queries-clear" @click="emit('clearRecent')">
							Clear
						</n-button>
					</header>
					<p v-if="!recent.length" class="text-tertiary m-0 px-3 py-3 text-xs">
						{{ loading ? "Loading…" : "The searches you run show up here." }}
					</p>
					<div v-else class="divide-border flex flex-col divide-y">
						<button
							v-for="(entry, index) of recent"
							:key="`${index}-${entry.ran_at}`"
							type="button"
							class="hover:bg-secondary/50 flex min-w-0 cursor-pointer flex-col gap-0.5 px-3 py-2 text-left"
							data-testid="recent-query"
							@click="pick(entry)"
						>
							<span class="text-default truncate font-mono text-xs [font-variant-ligatures:none]">{{ entry.query || "*" }}</span>
							<span class="text-tertiary truncate text-xs">
								{{ entry.source_name }} · {{ timeLabel(entry) }} · {{ relative(entry.ran_at) }}
							</span>
						</button>
					</div>
				</section>
			</div>
		</n-popover>

		<n-popover v-model:show="showSave" trigger="click" placement="bottom-start" @update:show="onSaveShown">
			<template #trigger>
				<n-button size="small" secondary :disabled="!available || !canSave" data-testid="save-query-toggle">
					<template #icon><Icon name="carbon:bookmark-add" /></template>
					Save
				</n-button>
			</template>
			<form class="flex w-[min(86vw,20rem)] flex-col gap-2" data-testid="save-query-form" @submit.prevent="submitSave">
				<span :class="HEAD" class="text-tertiary">Save this search as</span>
				<n-input
					ref="nameInput"
					v-model:value="name"
					size="small"
					placeholder="e.g. Failed logins on web servers"
					:maxlength="80"
					data-testid="save-query-name"
				/>
				<span v-if="willReplace" class="text-warning text-xs">Updates the query saved under this name.</span>
				<div class="flex justify-end gap-2">
					<n-button size="small" quaternary @click="showSave = false">Cancel</n-button>
					<n-button size="small" type="primary" attr-type="submit" :disabled="!name.trim()" data-testid="save-query-submit">
						Save
					</n-button>
				</div>
			</form>
		</n-popover>
	</div>
</template>

<script setup lang="ts">
import type { EventSearchRecentQuery, EventSearchSavedQuery, EventSearchState } from "@/types/siem"
import { NButton, NInput, NPopover } from "naive-ui"
import { computed, nextTick, ref, useTemplateRef } from "vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils/format"
import { describeTime } from "./eventSearchMemory"

/**
 * The saved and recent searches of event search (#1258), and saving the current one under
 * a name. Picking one hands it to the search form, which restores it and runs it.
 */

const { saved, recent, available, canSave, loading = false, error = null } = defineProps<{
	saved: EventSearchSavedQuery[]
	recent: EventSearchRecentQuery[]
	/** A user and a customer to remember for. */
	available: boolean
	/** A source is selected: there is a search to save. */
	canSave: boolean
	/** The memory is being read from the server. */
	loading?: boolean
	/** Why it could not be read. */
	error?: string | null
}>()

const emit = defineEmits<{
	(e: "restore", value: EventSearchState): void
	(e: "save", name: string): void
	(e: "delete", id: number): void
	(e: "clearRecent"): void
	(e: "retry"): void
}>()

const HEAD = "text-tertiary text-xxs font-medium tracking-[0.12em] uppercase"
const dFormats = useSettingsStore().dateFormat
const showList = ref(false)
const showSave = ref(false)
const name = ref("")
const nameInput = useTemplateRef<InstanceType<typeof NInput>>("nameInput")

const willReplace = computed(() => {
	const wanted = name.value.trim().toLowerCase()
	return !!wanted && saved.some(entry => entry.name.toLowerCase() === wanted)
})

const relative = (iso: string) => dayjs(iso).fromNow()
const timeLabel = (state: EventSearchState) => describeTime(state, iso => String(formatDate(iso, dFormats.datetime)))

function pick(state: EventSearchState) {
	showList.value = false
	emit("restore", state)
}

async function onSaveShown(show: boolean) {
	if (!show) return
	name.value = ""
	await nextTick()
	nameInput.value?.focus()
}

function submitSave() {
	if (!name.value.trim()) return
	emit("save", name.value)
	showSave.value = false
}
</script>
