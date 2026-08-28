<template>
	<n-modal
		:show="!!event"
		preset="card"
		segmented
		:style="{ width: 'min(780px, 94vw)', maxHeight: '90vh' }"
		content-class="p-0!"
		@update:show="value => !value && emit('close')"
	>
		<template #header>
			<div class="flex items-center gap-2">
				<Icon :name="LogIcon" :size="18" />
				<span class="font-semibold">Event details</span>
				<n-tag v-if="source" size="tiny" round :bordered="false">{{ source }}</n-tag>
			</div>
		</template>
		<template #header-extra>
			<n-button size="tiny" secondary @click="copyEventJson">
				<template #icon><Icon :name="CopyIcon" :size="14" /></template>
				Copy JSON
			</n-button>
		</template>

		<div class="border-default border-b px-4 pt-3 pb-3">
			<n-input v-model:value="filter" size="small" clearable placeholder="Filter fields…">
				<template #prefix><Icon :name="SearchIcon" :size="14" /></template>
			</n-input>
		</div>

		<n-scrollbar style="max-height: 68vh">
			<div class="flex flex-col gap-4 p-4">
				<div v-if="filteredPrimary.length" class="flex flex-col">
					<KeyValueRow v-for="[key, value] of filteredPrimary" :key :field="key" :value @copy="copyValue" />
				</div>

				<n-empty
					v-if="!filteredPrimary.length && !filteredInternal.length"
					description="No fields match your filter."
					class="py-8"
				/>

				<n-collapse v-if="filteredInternal.length" :default-expanded-names="filter ? ['internal'] : []">
					<n-collapse-item :title="`Graylog internal fields (${filteredInternal.length})`" name="internal">
						<div class="flex flex-col">
							<KeyValueRow
								v-for="[key, value] of filteredInternal"
								:key
								:field="key"
								:value
								@copy="copyValue"
							/>
						</div>
					</n-collapse-item>
				</n-collapse>
			</div>
		</n-scrollbar>
	</n-modal>
</template>

<script setup lang="ts">
import { useClipboard } from "@vueuse/core"
import { NButton, NCollapse, NCollapseItem, NEmpty, NInput, NModal, NScrollbar, NTag, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import KeyValueRow from "./KeyValueRow.vue"

const { event = null } = defineProps<{
	/** The raw Graylog message; `null` closes the modal. */
	event?: Record<string, unknown> | null
}>()

const emit = defineEmits<{ (e: "close"): void }>()

const LogIcon = "carbon:document"
const CopyIcon = "carbon:copy"
const SearchIcon = "carbon:search"

/** Shown first and in this order — the rest is alphabetical. */
const PRIMARY_ORDER = ["timestamp", "source", "message", "full_message"]

const message = useMessage()
const { copy, isSupported } = useClipboard()
const filter = ref("")

// A fresh event deserves a fresh filter, otherwise the previous query silently
// hides most of the new one's fields.
watch(
	() => event,
	() => (filter.value = "")
)

const source = computed(() => (event?.source ? String(event.source) : ""))

function isInternal(key: string): boolean {
	return key.startsWith("gl2_") || key === "streams"
}

function fmtVal(value: unknown): string {
	if (value === null || value === undefined) return ""
	if (typeof value === "object") return JSON.stringify(value)
	return String(value)
}

const primaryEntries = computed<[string, string][]>(() => {
	if (!event) return []
	const ordered: [string, string][] = PRIMARY_ORDER.filter(k => k in event && fmtVal(event[k]) !== "").map(k => [
		k,
		fmtVal(event[k])
	])
	const rest = Object.keys(event)
		.filter(k => !PRIMARY_ORDER.includes(k) && !isInternal(k))
		.sort()
		.map(k => [k, fmtVal(event[k])] as [string, string])

	return [...ordered, ...rest]
})

const internalEntries = computed<[string, string][]>(() =>
	event
		? Object.keys(event)
				.filter(isInternal)
				.sort()
				.map(k => [k, fmtVal(event[k])] as [string, string])
		: []
)

function matchFilter(entries: [string, string][]): [string, string][] {
	const query = filter.value.trim().toLowerCase()
	if (!query) return entries
	return entries.filter(([k, v]) => k.toLowerCase().includes(query) || v.toLowerCase().includes(query))
}

const filteredPrimary = computed(() => matchFilter(primaryEntries.value))
const filteredInternal = computed(() => matchFilter(internalEntries.value))

async function copyValue(value: string) {
	if (!isSupported.value) {
		message.error("Couldn't copy to clipboard")
		return
	}
	await copy(value)
	message.success("Value copied")
}

async function copyEventJson() {
	if (!event) return
	if (!isSupported.value) {
		message.error("Couldn't copy to clipboard")
		return
	}
	await copy(JSON.stringify(event, null, 2))
	message.success("Event JSON copied to clipboard")
}
</script>
