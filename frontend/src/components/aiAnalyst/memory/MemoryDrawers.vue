<template>
	<div class="flex flex-col gap-3" data-testid="talon-memory-drawers">
		<div class="flex flex-wrap items-end gap-3" role="search" aria-label="Filter memories">
			<label class="flex min-w-60 grow flex-col gap-1">
				<span class="text-secondary text-xs">Search (by meaning)</span>
				<n-input
					v-model:value="search"
					size="small"
					clearable
					:maxlength="MAX_QUERY"
					placeholder="e.g. backups on the file server"
					:input-props="{ 'aria-label': 'Search memories' }"
					data-testid="talon-memory-search"
				>
					<template #prefix><Icon name="carbon:search" :size="14" /></template>
				</n-input>
			</label>
			<label class="flex flex-col gap-1">
				<span class="text-secondary text-xs">Room</span>
				<n-select
					:value="room"
					:options="roomOptions"
					placeholder="Any room"
					clearable
					size="small"
					class="w-44!"
					data-testid="talon-memory-room"
					@update:value="emit('update:room', $event ?? null)"
				/>
			</label>
			<label class="flex flex-col gap-1">
				<span class="text-secondary text-xs">Source</span>
				<n-select
					:value="source"
					:options="sourceOptions"
					placeholder="Any source"
					clearable
					size="small"
					class="w-48!"
					data-testid="talon-memory-source"
					@update:value="emit('update:source', $event ?? null)"
				/>
			</label>
			<label class="flex flex-col gap-1">
				<span class="text-secondary text-xs">Filed (UTC days)</span>
				<n-date-picker
					v-model:formatted-value="range"
					type="daterange"
					value-format="yyyy-MM-dd"
					clearable
					size="small"
					data-testid="talon-memory-range"
				/>
			</label>
		</div>

		<p v-if="query" class="text-tertiary text-xs" data-testid="talon-memory-search-note">
			Closest matches to your search, best first.
		</p>

		<MemoryProblem v-if="problem" :state="problem" @retry="load()" />

		<n-spin :show="loading && items.length > 0">
			<div
				v-if="loading && !items.length"
				class="flex justify-center py-10"
				data-testid="talon-memory-drawers-loading"
			>
				<n-spin size="small" />
			</div>
			<n-empty
				v-else-if="!problem && !items.length"
				:description="
					filtered ? 'No memory matches these filters' : 'Talon has no memories for this customer yet'
				"
				class="py-10"
				data-testid="talon-memory-drawers-empty"
			/>
			<div v-else-if="items.length" class="overflow-x-auto">
				<n-table size="small" :bordered="false" data-testid="talon-memory-table">
					<thead>
						<tr>
							<th class="whitespace-nowrap">Filed</th>
							<th>Room</th>
							<th>Source</th>
							<th class="w-full">Memory</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="row of items"
							:key="row.drawer_id"
							data-testid="talon-memory-row"
							:data-drawer="row.drawer_id"
						>
							<td class="whitespace-nowrap">{{ formatTime(row.filed_at) }}</td>
							<td class="whitespace-nowrap">
								<bdi>{{ roomText(row.room, row.room_name) }}</bdi>
							</td>
							<td class="whitespace-nowrap">{{ sourceLabel(row.source) }}</td>
							<td>
								<div class="flex flex-col gap-1">
									<button
										v-if="row.openable"
										type="button"
										class="text-default hover:text-primary focus-visible:text-primary line-clamp-2 cursor-pointer text-left break-words"
										:aria-label="`Open memory: ${row.preview ?? row.drawer_id}`"
										data-testid="talon-memory-open"
										@click="emit('open', row)"
									>
										<bdi>{{ row.preview ?? "(no preview)" }}</bdi>
									</button>
									<span
										v-else
										class="text-secondary line-clamp-2 break-words"
										title="This memory's id can't be opened from CoPilot"
									>
										<bdi>{{ row.preview ?? "(no preview)" }}</bdi>
									</span>
									<span class="flex flex-wrap gap-1">
										<n-tag
											v-if="row.durable"
											size="tiny"
											:bordered="false"
											data-testid="talon-memory-durable"
										>
											Durable
										</n-tag>
										<n-tag
											v-if="hiddenTag(row)"
											size="tiny"
											:type="hiddenTag(row)?.type"
											:bordered="false"
											:title="hiddenTag(row)?.title"
											data-testid="talon-memory-hidden-tag"
										>
											<template #icon><Icon name="carbon:view-off" :size="12" /></template>
											{{ hiddenTag(row)?.text }}
										</n-tag>
									</span>
								</div>
							</td>
						</tr>
					</tbody>
				</n-table>
			</div>
		</n-spin>

		<div v-if="items.length" class="flex flex-wrap items-center justify-between gap-2">
			<span class="text-tertiary text-xs" aria-live="polite" data-testid="talon-memory-count">
				{{ items.length }} shown{{ nextCursor ? "; more are available" : "" }}
			</span>
			<n-button
				v-if="nextCursor"
				size="small"
				secondary
				:loading="loadingMore"
				:disabled="loading || loadingMore"
				data-testid="talon-memory-more"
				@click="loadMore()"
			>
				Load more
			</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
// A customer's memories, newest first: room, source and date filters, a search by meaning
// (debounced; talon-analyst's semantic search, which may not page) and cursor paging ("Load more"
// asks for the next page with the cursor Talon gave). Opening a row emits it; the detail drawer is
// the parent's.
import type { TalonMemoryFailure } from "@/api/endpoints/talonMemory"
import type { TalonMemoryItem, TalonMemoryRoom, TalonMemorySource } from "@/types/talonMemory"
import { watchDebounced } from "@vueuse/core"
import { NButton, NDatePicker, NEmpty, NInput, NSelect, NSpin, NTable, NTag } from "naive-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import Api from "@/api"
import { memoryFailure } from "@/api/endpoints/talonMemory"
import Icon from "@/components/common/Icon.vue"
import { formatTime } from "../health/health"
import {
	dateParams,
	hiddenTag,
	PAGE_SIZE,
	problemState,
	ROOM_FILTERS,
	roomText,
	SEARCH_DEBOUNCE_MS,
	sourceLabel,
	SOURCES
} from "./memory"
import MemoryProblem from "./MemoryProblem.vue"

const {
	customerCode,
	room = null,
	source = null
} = defineProps<{
	customerCode: string
	room?: TalonMemoryRoom | null
	source?: TalonMemorySource | null
}>()
const emit = defineEmits<{
	(e: "open", item: TalonMemoryItem): void
	(e: "update:room", value: TalonMemoryRoom | null): void
	(e: "update:source", value: TalonMemorySource | null): void
}>()

/** The backend's cap on a search (`services/talon_memory.py:MAX_QUERY`). */
const MAX_QUERY = 200

const roomOptions = ROOM_FILTERS.map(r => ({ label: r.label, value: r.value }))
const sourceOptions = SOURCES.map(s => ({ label: s.label, value: s.value }))

const search = ref<string | null>(null)
const query = ref<string | null>(null)
const range = ref<[string, string] | null>(null)
const items = ref<TalonMemoryItem[]>([])
const nextCursor = ref<string | null>(null)
const failure = ref<TalonMemoryFailure | null>(null)
const loading = ref(false)
const loadingMore = ref(false)
let controller: AbortController | null = null

const problem = computed(() => problemState(failure.value))
const filtered = computed(() => !!(room || source || query.value || range.value))

function params(cursor: string | null) {
	const { since, before } = dateParams(range.value)
	return { room, source, q: query.value, since, before, limit: PAGE_SIZE, cursor }
}

async function fetchPage(cursor: string | null) {
	controller?.abort()
	const own = new AbortController()
	controller = own
	failure.value = null
	try {
		const { data } = await Api.talonMemory.listDrawers(customerCode, params(cursor), own.signal)
		if (controller !== own) return
		const seen = new Set(cursor ? items.value.map(i => i.drawer_id) : [])
		const page = (data.items ?? []).filter(i => !seen.has(i.drawer_id))
		items.value = cursor ? [...items.value, ...page] : page
		nextCursor.value = data.next_cursor ?? null
	} catch (err) {
		if (controller !== own || own.signal.aborted) return
		failure.value = memoryFailure(err)
		if (!cursor) {
			items.value = []
			nextCursor.value = null
		}
	}
}

// Bumped by each first-page load: only the newest one clears the spinner.
let generation = 0

async function load() {
	const mine = ++generation
	loading.value = true
	try {
		await fetchPage(null)
	} finally {
		if (mine === generation) loading.value = false
	}
}

async function loadMore() {
	if (!nextCursor.value) return
	loadingMore.value = true
	try {
		await fetchPage(nextCursor.value)
	} finally {
		loadingMore.value = false
	}
}

/** A forgotten memory leaves the list at once. */
function remove(drawerId: string) {
	items.value = items.value.filter(i => i.drawer_id !== drawerId)
}

defineExpose({ reload: load, remove })

// The search waits for the typing to stop; every other filter applies at once.
watchDebounced(
	search,
	value => {
		const text = (value ?? "").trim()
		query.value = text ? text.slice(0, MAX_QUERY) : null
	},
	{ debounce: SEARCH_DEBOUNCE_MS }
)
watch([() => customerCode, () => room, () => source, query, () => range.value?.join(",")], () => load(), {
	immediate: true
})
onBeforeUnmount(() => controller?.abort())
</script>
