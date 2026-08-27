<template>
	<!-- Card form: the label and count ride in the card header, the filter sits at
	     the top of the body so collapsing the card takes the control with it. -->
	<CollapsibleCard v-if="card" :collapsible :default-collapsed>
		<template #header>
			<span :class="SECTION_LABEL">
				{{ label }}
				<span class="text-tertiary normal-case">{{ countLabel }}</span>
			</span>
			<slot name="header-extra" />
		</template>

		<div v-if="filterKeys" class="border-default border-b p-3">
			<n-input
				v-model:value="query"
				size="small"
				clearable
				:placeholder="filterPlaceholder"
				class="w-full sm:w-72"
			>
				<template #prefix><Icon :name="SearchIcon" :size="14" /></template>
			</n-input>
		</div>

		<n-scrollbar :style="{ maxHeight }">
			<div class="divide-border flex flex-col divide-y">
				<div v-for="(item, index) of results" :key="index" class="px-3 py-2" :class="rowClass">
					<slot name="item" :item :index />
				</div>
				<div v-if="!results.length" class="text-tertiary px-3 py-4 text-xs">{{ emptyText }}</div>
			</div>
		</n-scrollbar>
	</CollapsibleCard>

	<!-- Inline form, for a list nested inside a card that already exists: the label
	     and the filter share one row above the box, the way ValueList's label sits
	     outside the frame. -->
	<div v-else class="flex flex-col gap-2">
		<div class="flex flex-wrap items-center justify-between gap-2">
			<span :class="SECTION_LABEL">
				{{ label }}
				<span class="text-tertiary normal-case">{{ countLabel }}</span>
			</span>
			<slot name="header-extra" />
			<n-input
				v-if="filterKeys"
				v-model:value="query"
				size="small"
				clearable
				:placeholder="filterPlaceholder"
				class="w-full sm:w-64"
			>
				<template #prefix><Icon :name="SearchIcon" :size="14" /></template>
			</n-input>
		</div>

		<div class="border-default rounded-lg border">
			<n-scrollbar :style="{ maxHeight }">
				<div class="divide-border flex flex-col divide-y">
					<div v-for="(item, index) of results" :key="index" class="px-3 py-2" :class="rowClass">
						<slot name="item" :item :index />
					</div>
					<div v-if="!results.length" class="text-tertiary px-3 py-4 text-xs">{{ emptyText }}</div>
				</div>
			</n-scrollbar>
		</div>
	</div>
</template>

<script setup lang="ts" generic="T">
/**
 * A scrollable list of rows with an optional client-side filter.
 *
 * The shape — label, a filtered/total count, a search box, then hairline-separated
 * rows inside a bounded scroll area — was hand-written five times across the file
 * analysis tabs, each with its own padding, input size and empty-state wording.
 * Only the row content ever really differed, so that is all a caller supplies.
 *
 * Rows are keyed by index on purpose: the lists this renders (MITRE techniques,
 * YARA hits, processes) legitimately repeat a value, and keying by the value
 * itself is how duplicate-key warnings get in.
 */
import { NInput, NScrollbar } from "naive-ui"
import { computed, watch } from "vue"
import CollapsibleCard from "@/components/common/CollapsibleCard.vue"
import Icon from "@/components/common/Icon.vue"
import { useFuseFilter } from "@/components/common/searchDialog.helpers"
import { SECTION_LABEL } from "@/components/common/section-label"

const props = withDefaults(
	defineProps<{
		items: T[]
		label: string
		/** Fields Fuse searches. Omit to render the list without a filter at all. */
		filterKeys?: string[]
		filterPlaceholder?: string
		maxHeight?: string
		emptyText?: string
		/** false nests the list inside a card that already exists. */
		card?: boolean
		collapsible?: boolean
		defaultCollapsed?: boolean
		/** Layout classes for each row; the padding is supplied either way. */
		rowClass?: string
	}>(),
	{
		filterPlaceholder: "Filter…",
		maxHeight: "18rem",
		emptyText: "Nothing matches that filter.",
		card: true,
		collapsible: true,
		defaultCollapsed: false,
		rowClass: ""
	}
)

// A caller sometimes needs to know that a filter is active — a tree, for one,
// must flatten while filtering, because indentation that points at a parent the
// filter removed describes a hierarchy that is not on screen.
const emit = defineEmits<{ (e: "update:query", value: string): void }>()

defineSlots<{
	"item": (props: { item: T; index: number }) => unknown
	"header-extra": () => unknown
}>()

const SearchIcon = "carbon:search"

const { query, results: filtered } = useFuseFilter<T>(
	() => props.items ?? [],
	// Fuse is only built when there is something to search; the keys are read
	// through a getter so an absent filter never indexes the list.
	props.filterKeys ?? []
)

watch(query, value => emit("update:query", value))

const results = computed(() => (props.filterKeys ? filtered.value : (props.items ?? [])))

// "12/40" while filtering, plain "40" otherwise — a ratio that never changes is
// just noise next to the label.
const countLabel = computed(() => {
	const total = props.items?.length ?? 0
	if (props.filterKeys && results.value.length !== total) return `(${results.value.length}/${total})`
	return `(${total})`
})
</script>
