<template>
	<div class="flex flex-col gap-1" data-testid="talon-v2-thread-list">
		<div
			v-for="thread of threads"
			:key="thread.id"
			class="group hover:bg-secondary flex cursor-pointer flex-col gap-1 rounded-md px-2 py-1.5"
			:class="{ 'bg-secondary': thread.id === selectedId }"
			data-testid="talon-v2-thread"
			:data-thread-id="thread.id"
			:aria-current="thread.id === selectedId ? 'true' : undefined"
			@click="editingId !== thread.id && confirmingId !== thread.id && emit('select', thread)"
		>
			<div v-if="editingId === thread.id" class="flex items-center gap-1" @click.stop>
				<n-input
					v-model:value="draft"
					size="tiny"
					:maxlength="TITLE_MAX"
					placeholder="Thread title"
					data-testid="talon-v2-rename-input"
					@keydown.enter.prevent="saveRename(thread)"
					@keydown.esc.prevent="cancelRename()"
				/>
				<n-button size="tiny" text data-testid="talon-v2-rename-save" @click="saveRename(thread)">
					<Icon name="carbon:checkmark" :size="14" />
				</n-button>
				<n-button size="tiny" text @click="cancelRename()">
					<Icon name="carbon:close" :size="14" />
				</n-button>
			</div>
			<div v-else class="flex items-center gap-1.5">
				<Icon
					v-if="!thread.accessible"
					name="carbon:locked"
					:size="13"
					class="text-warning shrink-0"
					data-testid="talon-v2-thread-locked"
					aria-label="Customer access removed"
				/>
				<span class="grow truncate text-sm" data-testid="talon-v2-thread-title">
					{{ thread.title || "Untitled thread" }}
				</span>
				<div
					v-if="confirmingId !== thread.id"
					class="flex shrink-0 items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100"
					:class="{ 'opacity-100': thread.id === selectedId }"
				>
					<n-button
						size="tiny"
						text
						title="Rename"
						data-testid="talon-v2-thread-rename"
						@click.stop="startRename(thread)"
					>
						<Icon name="carbon:edit" :size="13" />
					</n-button>
					<n-button
						v-if="thread.status !== 'archived'"
						size="tiny"
						text
						title="Archive"
						data-testid="talon-v2-thread-archive"
						@click.stop="confirmingId = thread.id"
					>
						<Icon name="carbon:archive" :size="13" />
					</n-button>
				</div>
			</div>

			<div v-if="confirmingId === thread.id" class="flex items-center gap-2 text-xs" @click.stop>
				<span class="text-secondary">Archive this thread?</span>
				<n-button
					size="tiny"
					type="warning"
					secondary
					data-testid="talon-v2-archive-confirm"
					@click="archive(thread)"
				>
					Archive
				</n-button>
				<n-button size="tiny" secondary @click="confirmingId = null">Cancel</n-button>
			</div>

			<div class="flex items-center gap-1.5">
				<n-tag
					size="tiny"
					:bordered="false"
					:type="thread.customer_code ? 'info' : 'default'"
					data-testid="talon-v2-thread-customer"
				>
					{{ thread.customer_code ?? "General" }}
				</n-tag>
				<n-tag v-if="thread.status === 'archived'" size="tiny" :bordered="false" type="warning">Archived</n-tag>
			</div>
		</div>

		<div
			v-if="!threads.length && !loading"
			class="text-tertiary px-2 py-4 text-center text-xs"
			data-testid="talon-v2-no-threads"
		>
			No threads yet.
		</div>
		<div v-if="hasMore" class="flex justify-center py-1">
			<n-button size="tiny" text :loading data-testid="talon-v2-threads-more" @click="emit('load-more')">
				More
			</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
// The thread rail's list: each of the caller's v2 threads with its customer ("General" for a
// thread with no customer data) and a lock when that customer is no longer theirs. Rename and
// archive are asked of the parent, which calls talon-analyst. Titles are text.
import type { TalonV2Thread } from "@/types/talonV2"
import { NButton, NInput, NTag } from "naive-ui"
import { ref } from "vue"
import Icon from "@/components/common/Icon.vue"

const {
	threads,
	selectedId = null,
	loading = false,
	hasMore = false
} = defineProps<{
	threads: TalonV2Thread[]
	selectedId?: string | null
	loading?: boolean
	hasMore?: boolean
}>()

const emit = defineEmits<{
	(e: "select", thread: TalonV2Thread): void
	/** `title: null` clears the title. */
	(e: "rename", thread: TalonV2Thread, title: string | null): void
	(e: "archive", thread: TalonV2Thread): void
	(e: "load-more"): void
}>()

/** talon-analyst's limit on a title. */
const TITLE_MAX = 200

const editingId = ref<string | null>(null)
const confirmingId = ref<string | null>(null)
const draft = ref("")

function startRename(thread: TalonV2Thread) {
	confirmingId.value = null
	editingId.value = thread.id
	draft.value = thread.title ?? ""
}

function cancelRename() {
	editingId.value = null
	draft.value = ""
}

function saveRename(thread: TalonV2Thread) {
	const title = draft.value.trim()
	cancelRename()
	if (title === (thread.title ?? "")) return
	emit("rename", thread, title || null)
}

function archive(thread: TalonV2Thread) {
	confirmingId.value = null
	emit("archive", thread)
}
</script>
