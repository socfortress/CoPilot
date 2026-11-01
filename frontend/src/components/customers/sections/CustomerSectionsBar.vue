<template>
	<div class="customer-sections-bar" data-testid="customer-sections-bar">
		<n-popover
			v-model:show="pinnedOpen"
			trigger="click"
			placement="bottom-start"
			:show-arrow="false"
			content-class="p-1!"
		>
			<template #trigger>
				<button
					type="button"
					class="bar-button"
					aria-haspopup="menu"
					:aria-expanded="pinnedOpen"
					data-testid="sections-pinned"
				>
					<Icon name="carbon:pin-filled" :size="14" class="text-primary" />
					Pinned
					<span class="bar-count">{{ pinnedSections.length }}</span>
					<Icon name="carbon:chevron-down" :size="12" class="text-secondary" />
				</button>
			</template>
			<div class="pinned-menu" role="menu" aria-label="Pinned sections" data-testid="sections-pinned-menu">
				<p v-if="!pinnedSections.length" class="text-secondary px-2 py-2 text-sm">
					Nothing pinned yet. Pin a section from its toolbar to reach it from here on every customer.
				</p>
				<div v-for="section of pinnedSections" :key="section.id" class="pinned-row">
					<button
						type="button"
						role="menuitem"
						class="pinned-item"
						:class="{ 'is-current': section.id === current }"
						:data-testid="`sections-pinned-item-${section.id}`"
						@click="choose(section.id)"
					>
						<SectionMark :state="sectionState(section, status)" />
						<span class="min-w-0 flex-1 truncate text-left">{{ section.label }}</span>
						<span class="text-secondary font-mono text-[11px]">{{ groupById(section.group).label }}</span>
					</button>
					<n-button
						quaternary
						size="tiny"
						:aria-label="`Unpin ${section.label}`"
						:data-testid="`sections-unpin-${section.id}`"
						@click="emit('togglePin', section.id)"
					>
						<template #icon><Icon name="carbon:close" :size="14" /></template>
					</n-button>
				</div>
			</div>
		</n-popover>

		<span class="bar-divider" aria-hidden="true"></span>

		<nav class="bar-groups" aria-label="Customer sections">
			<template v-for="group of groups" :key="group.id">
				<button
					v-if="group.sections.length === 1"
					type="button"
					class="bar-button bar-group"
					:class="{ 'is-current': group.id === currentGroup }"
					:aria-current="group.id === currentGroup ? 'true' : undefined"
					:data-testid="`section-group-${group.id}`"
					@click="emit('openGroup', group.id)"
				>
					{{ group.label }}
				</button>
				<n-popover
					v-else
					:show="openGroup === group.id"
					trigger="hover"
					placement="bottom-start"
					:show-arrow="false"
					:delay="120"
					to="body"
					:duration="80"
					@update:show="(show: boolean) => setOpenGroup(group.id, show)"
				>
					<template #trigger>
						<button
							:ref="el => setGroupButton(group.id, el)"
							type="button"
							class="bar-button bar-group"
							:class="{ 'is-current': group.id === currentGroup, 'is-open': openGroup === group.id }"
							aria-haspopup="menu"
							:aria-expanded="openGroup === group.id"
							:aria-current="group.id === currentGroup ? 'true' : undefined"
							:data-testid="`section-group-${group.id}`"
							@click="openGroupFromMenu(group.id)"
							@keydown.down.prevent="openFromKeyboard(group.id)"
						>
							{{ group.label }}
							<Icon
								:name="openGroup === group.id ? 'carbon:chevron-up' : 'carbon:chevron-down'"
								:size="12"
								class="text-secondary"
							/>
						</button>
					</template>
					<SectionGroupMenu
						:group
						:status
						:current
						:focus-first="keyboardGroup === group.id"
						@select="choose"
						@open-group="openGroupFromMenu(group.id)"
						@close="closeMenu(group.id)"
						@focusout="onMenuFocusOut($event, group.id)"
					/>
				</n-popover>
			</template>
		</nav>

		<div class="bar-search" data-testid="sections-search">
			<n-auto-complete
				ref="search"
				v-model:value="query"
				to="body"
				clearable
				:options="searchOptions"
				:render-label="renderOption"
				:get-show="(value: string) => !!value.trim()"
				:input-props="{ 'aria-label': 'Find a section' }"
				placeholder="Find a section"
				size="small"
				blur-after-select
				@select="onSearchSelect"
			>
				<template #prefix><Icon name="carbon:search" :size="14" /></template>
				<template #suffix><kbd class="bar-kbd">/</kbd></template>
			</n-auto-complete>
		</div>
	</div>
</template>

<script setup lang="tsx">
import type { AutoCompleteInst, SelectOption } from "naive-ui"
import type { ComponentPublicInstance } from "vue"
import type { GroupId, GroupView, SectionDef, SectionId } from "./sections"
import type { CustomerSectionStatus } from "@/types/customers"
import { onKeyStroke } from "@vueuse/core"
import { NAutoComplete, NButton, NPopover } from "naive-ui"
import { computed, nextTick, ref, useTemplateRef } from "vue"
import Icon from "@/components/common/Icon.vue"
import SectionGroupMenu from "./SectionGroupMenu.vue"
import SectionMark from "./SectionMark.vue"
import { groupById, searchSections, sectionById, sectionState } from "./sections"

/**
 * The bar above a customer's sections (#1325): the pinned sections, one menu per group that
 * previews what each section holds before it is opened, and a search over every section.
 */
const { groups, sections, current, status, pinned } = defineProps<{
	groups: GroupView[]
	/** Every section the viewer may open, for the search and the pinned list. */
	sections: SectionDef[]
	current: SectionId
	status: CustomerSectionStatus | null
	pinned: SectionId[]
}>()

const emit = defineEmits<{
	(e: "select", id: SectionId): void
	(e: "openGroup", id: GroupId): void
	(e: "togglePin", id: SectionId): void
}>()

const currentGroup = computed(() => sectionById(current).group)

const pinnedSections = computed(() =>
	pinned.map(id => sections.find(section => section.id === id)).filter((section): section is SectionDef => !!section)
)
const pinnedOpen = ref(false)

const openGroup = ref<GroupId | null>(null)
const keyboardGroup = ref<GroupId | null>(null)
const groupButtons = new Map<GroupId, HTMLElement>()

function setGroupButton(id: GroupId, el: Element | ComponentPublicInstance | null) {
	if (el instanceof HTMLElement) groupButtons.set(id, el)
	else groupButtons.delete(id)
}

function setOpenGroup(id: GroupId, show: boolean) {
	if (show) {
		openGroup.value = id
	} else if (openGroup.value === id) {
		openGroup.value = null
		keyboardGroup.value = null
	}
}

function openFromKeyboard(id: GroupId) {
	keyboardGroup.value = id
	openGroup.value = id
}

function closeMenu(id: GroupId) {
	setOpenGroup(id, false)
	nextTick(() => groupButtons.get(id)?.focus())
}

function onMenuFocusOut(event: FocusEvent, id: GroupId) {
	const next = event.relatedTarget as Node | null
	const menu = event.currentTarget as HTMLElement | null
	if (next && (menu?.contains(next) || groupButtons.get(id)?.contains(next))) return
	if (keyboardGroup.value === id) setOpenGroup(id, false)
}

function choose(id: SectionId) {
	openGroup.value = null
	keyboardGroup.value = null
	pinnedOpen.value = false
	emit("select", id)
}

function openGroupFromMenu(id: GroupId) {
	openGroup.value = null
	keyboardGroup.value = null
	emit("openGroup", id)
}

const query = ref("")
const searchOptions = computed(() =>
	searchSections(query.value, sections).map(section => ({ label: section.label, value: section.id }))
)

// Plain elements only: Naive keeps an option's label nodes across its menu's renders, and a
// component inside them was patched after the menu had unmounted it.
// The page changes section only once the search has closed its menu: switching in the same tick
// had Vue patch the menu's options after Naive unmounted them ("emitsOptions" of null).
function onSearchSelect(value: string | number) {
	setTimeout(() => {
		// Naive writes the chosen option's label into the field: the search starts empty again.
		query.value = ""
		choose(value as SectionId)
	}, 0)
}

function renderOption(option: SelectOption) {
	const section = sectionById(option.value as SectionId)
	const state = sectionState(section, status)
	// The section's name is never cut: the group beside it gives way first.
	return (
		<span class="flex w-full min-w-0 items-center gap-2" data-testid={`sections-search-option-${section.id}`}>
			<span class="shrink-0">{section.label}</span>
			{state ? <span class="text-secondary shrink-0 text-xs">{state.word}</span> : null}
			<span class="text-secondary ml-auto min-w-0 truncate font-mono text-[11px]">
				{groupById(section.group).label}
			</span>
		</span>
	)
}

const search = useTemplateRef<AutoCompleteInst>("search")

function typingSomewhere(target: EventTarget | null): boolean {
	const element = target as HTMLElement | null
	if (!element) return false
	return element.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(element.tagName)
}

// "/" finds a section, as on the rest of the console's search fields, unless the viewer is typing.
onKeyStroke("/", event => {
	if (event.ctrlKey || event.metaKey || event.altKey || typingSomewhere(event.target)) return
	if (!search.value) return
	event.preventDefault()
	search.value.focus()
})
</script>

<style lang="scss" scoped>
.customer-sections-bar {
	display: flex;
	align-items: center;
	gap: 6px;
	min-height: 48px;
	padding: 0 16px;
	background-color: var(--bg-secondary-color);
	border-bottom: 1px solid var(--border-color);

	.bar-groups {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 4px;
		min-width: 0;
	}

	.bar-button {
		position: relative;
		display: inline-flex;
		align-items: center;
		gap: 6px;
		height: 32px;
		padding: 0 10px;
		border-radius: var(--border-radius-small);
		font-size: 14px;
		white-space: nowrap;
		color: var(--fg-default-color);

		&:hover,
		&.is-open {
			background-color: var(--hover-color);
		}

		&:focus-visible {
			outline: 2px solid var(--primary-color);
			outline-offset: -2px;
		}
	}

	.bar-group.is-current {
		color: var(--primary-color);
	}

	.bar-count {
		font-family: var(--font-family-mono);
		font-size: 11px;
		color: var(--fg-secondary-color);
	}

	.bar-divider {
		width: 1px;
		height: 20px;
		margin: 0 4px;
		background-color: var(--border-color);
	}

	.bar-search {
		width: 300px;
		margin-left: auto;
		flex-shrink: 0;
	}

	.bar-kbd {
		font-family: var(--font-family-mono);
		font-size: 11px;
		line-height: 16px;
		padding: 0 5px;
		border: 1px solid var(--border-color);
		border-radius: 4px;
		color: var(--fg-secondary-color);
	}

	// Sized by the customer page's own width (the page, a modal, a phone), never the window's:
	// where the groups and the search don't fit on one line, the groups take a line of their own
	// and wrap, so no group is ever cut off behind a hidden scroll.
	@container customer-sections (max-width: 1200px) {
		flex-wrap: wrap;
		row-gap: 0;
		padding: 6px 12px 0;

		.bar-groups {
			order: 3;
			width: 100%;
			padding: 4px 0;
		}

		.bar-divider {
			display: none;
		}

		.bar-search {
			flex: 1 1 240px;
			max-width: 340px;
		}

		.bar-group.is-current::after {
			bottom: -4px;
		}
	}
}

.pinned-menu {
	width: 300px;
	max-width: calc(100vw - 32px);

	.pinned-row {
		display: flex;
		align-items: center;
		gap: 2px;
	}

	.pinned-item {
		display: flex;
		flex: 1;
		min-width: 0;
		align-items: center;
		gap: 10px;
		height: 34px;
		padding: 0 8px;
		border-radius: var(--border-radius-small);
		font-size: 14px;

		&:hover,
		&:focus-visible {
			background-color: var(--hover-color);
		}

		&.is-current {
			color: var(--primary-color);
		}
	}
}
</style>
