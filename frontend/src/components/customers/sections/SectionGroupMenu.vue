<template>
	<div
		ref="menu"
		class="section-group-menu"
		:class="{ 'is-wide': wide }"
		role="menu"
		:aria-label="group.label"
		:data-testid="`section-menu-${group.id}`"
		@keydown="onKeydown"
	>
		<header class="menu-head">
			<span class="font-semibold">{{ group.label }}</span>
			<span v-if="summary" class="text-secondary flex items-center gap-1.5 text-xs">
				<span class="summary-led" aria-hidden="true"></span>
				{{ summary }}
			</span>
			<button
				type="button"
				role="menuitem"
				class="open-group text-primary ml-auto text-xs"
				data-testid="section-menu-open-group"
				@click="emit('openGroup')"
			>
				Open group →
			</button>
		</header>

		<div class="menu-columns">
			<div v-for="subgroup of group.subgroups" :key="subgroup.label" class="menu-subgroup" role="group">
				<div v-if="subgroup.label" class="menu-subgroup-label">{{ subgroup.label }}</div>
				<button
					v-for="section of subgroup.sections"
					:key="section.id"
					type="button"
					role="menuitem"
					class="menu-item"
					:class="{ 'is-current': section.id === current }"
					:aria-current="section.id === current ? 'page' : undefined"
					:data-testid="`section-menu-item-${section.id}`"
					@click="emit('select', section.id)"
				>
					<span class="min-w-0 flex-1 truncate text-left">{{ section.label }}</span>
					<SectionMark :state="sectionState(section, status)" with-word />
				</button>
			</div>
		</div>

		<footer v-if="hasSwitches" class="menu-legend text-secondary text-xs" aria-hidden="true">
			<span class="flex items-center gap-1.5"><span class="legend-led is-on"></span>On for this customer</span>
			<span class="flex items-center gap-1.5"><span class="legend-led"></span>Off</span>
		</footer>
	</div>
</template>

<script setup lang="ts">
import type { GroupView, SectionId } from "./sections"
import type { CustomerSectionStatus } from "@/types/customers"
import { computed, onMounted, useTemplateRef } from "vue"
import SectionMark from "./SectionMark.vue"
import { sectionState, switchSummary } from "./sections"

/**
 * A group's sections, previewed before opening them (#1325): each with its state for this
 * customer, so "is the SLA page on?" is answered without leaving the section in view.
 */
const { group, status, current, focusFirst = false } = defineProps<{
	group: GroupView
	status: CustomerSectionStatus | null
	current: SectionId
	/** Move focus into the menu when it opens (it was opened from the keyboard). */
	focusFirst?: boolean
}>()

const emit = defineEmits<{
	(e: "select", id: SectionId): void
	(e: "openGroup"): void
	(e: "close"): void
}>()

const menu = useTemplateRef("menu")

const summary = computed(() => switchSummary(group.sections, status))
const hasSwitches = computed(() => group.sections.some(section => sectionState(section, status)?.kind === "switch"))
const wide = computed(() => group.subgroups.length > 1 && group.sections.length > 5)

function items(): HTMLElement[] {
	return [...(menu.value?.querySelectorAll<HTMLElement>("[role='menuitem']") ?? [])]
}

function onKeydown(event: KeyboardEvent) {
	const list = items()
	const index = list.indexOf(document.activeElement as HTMLElement)
	const moves: Record<string, number> = { ArrowDown: 1, ArrowUp: -1 }
	if (event.key in moves) {
		event.preventDefault()
		const next = (index + (moves[event.key] ?? 0) + list.length) % list.length
		list[next]?.focus()
	} else if (event.key === "Home" || event.key === "End") {
		event.preventDefault()
		list[event.key === "Home" ? 0 : list.length - 1]?.focus()
	} else if (event.key === "Escape") {
		event.preventDefault()
		emit("close")
	}
}

onMounted(() => {
	if (focusFirst) items()[1]?.focus()
})
</script>

<style lang="scss" scoped>
.section-group-menu {
	width: 300px;
	max-width: calc(100vw - 32px);
	padding: 4px;

	&.is-wide {
		width: 520px;

		.menu-columns {
			columns: 2;
		}
	}

	.menu-head {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 2px 8px 8px;
		border-bottom: 1px solid var(--border-color);
	}

	.summary-led,
	.legend-led {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		box-sizing: border-box;
		border: 1.5px solid var(--fg-secondary-color);
	}

	.summary-led,
	.legend-led.is-on {
		border: 0;
		background-color: var(--success-color);
	}

	.open-group {
		border-radius: var(--border-radius-small);
		padding: 2px 4px;
	}

	.menu-columns {
		column-gap: 12px;
		padding-top: 2px;
	}

	.menu-subgroup {
		break-inside: avoid;
	}

	.menu-subgroup-label {
		padding: 8px 8px 4px;
		font-family: var(--font-family-mono);
		font-size: 10px;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--fg-secondary-color);
	}

	.menu-item {
		display: flex;
		align-items: center;
		gap: 10px;
		width: 100%;
		height: 32px;
		padding: 0 8px;
		border-radius: var(--border-radius-small);
		font-size: 14px;
		color: var(--fg-default-color);

		&:hover,
		&:focus-visible {
			background-color: var(--hover-color);
		}

		&.is-current {
			color: var(--primary-color);
		}
	}

	.menu-legend {
		display: flex;
		gap: 16px;
		margin-top: 6px;
		padding: 8px 8px 2px;
		border-top: 1px solid var(--border-color);
	}

	button:focus-visible {
		outline: 2px solid var(--primary-color);
		outline-offset: -2px;
	}
}
</style>
