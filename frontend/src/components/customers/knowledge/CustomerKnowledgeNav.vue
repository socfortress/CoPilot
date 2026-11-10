<template>
	<nav class="knowledge-nav" aria-label="Knowledge sections" data-testid="knowledge-nav">
		<div ref="track" class="knowledge-nav-track">
			<button
				v-for="link of links"
				:key="link.id"
				type="button"
				class="knowledge-nav-link"
				:class="{ 'is-active': link.id === active }"
				:aria-current="link.id === active ? 'true' : undefined"
				:data-nav-id="link.id"
				:data-testid="`knowledge-nav-${link.id}`"
				@click="emit('go', link.id)"
			>
				{{ link.label }}
				<span v-if="link.count !== undefined" class="knowledge-nav-count">{{ link.count }}</span>
			</button>
		</div>
	</nav>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from "vue"

export interface KnowledgeNavLink {
	id: string
	label: string
	/** How many facts the part holds; none for a part that isn't a list of facts. */
	count?: number
}

/**
 * The Knowledge pane's bar of jumps: one per group of facts and one for "What Talon sees". It stays
 * under the app's toolbar while the pane scrolls, and keeps the part in view inside its own row
 * when the row is wider than the pane (a phone).
 */
const { links, active } = defineProps<{
	links: KnowledgeNavLink[]
	active: string | null
}>()

const emit = defineEmits<{
	(e: "go", id: string): void
	/** The bar is in the page, and so are the parts beside it. */
	(e: "ready"): void
}>()

const track = ref<HTMLElement | null>(null)

onMounted(() => emit("ready"))

watch(
	() => active,
	id => {
		const link = id ? track.value?.querySelector<HTMLElement>(`[data-nav-id="${id}"]`) : null
		if (!link || !track.value) return
		// Only the row scrolls, sideways: scrollIntoView would move the page too.
		const row = track.value
		const left = link.offsetLeft - row.offsetLeft
		if (left < row.scrollLeft || left + link.offsetWidth > row.scrollLeft + row.clientWidth) {
			row.scrollTo({ left: left - 16 })
		}
	},
	{ flush: "post" }
)
</script>

<style lang="scss" scoped>
.knowledge-nav {
	position: sticky;
	top: 0;
	z-index: 2;
	margin: 0 -16px;
	padding: 8px 16px;
	padding-top: var(--toolbar-height);
	background-color: var(--bg-body-color);
	border-bottom: 1px solid var(--border-color);
}

.knowledge-nav-track {
	display: flex;
	gap: 4px;
	overflow-x: auto;
	scrollbar-width: none;

	&::-webkit-scrollbar {
		display: none;
	}
}

.knowledge-nav-link {
	display: inline-flex;
	flex-shrink: 0;
	align-items: center;
	gap: 6px;
	height: 30px;
	padding: 0 10px;
	border-radius: var(--border-radius-small);
	font-size: 13px;
	white-space: nowrap;
	color: var(--fg-secondary-color);

	&:hover {
		color: var(--fg-default-color);
		background-color: var(--hover-color);
	}

	&.is-active {
		color: var(--fg-default-color);
		background-color: var(--hover-color);
		font-weight: 600;
	}

	&:focus-visible {
		outline: 2px solid var(--primary-color);
		outline-offset: -2px;
	}
}

.knowledge-nav-count {
	font-family: var(--font-family-mono);
	font-size: 11px;
	font-weight: 400;
	color: var(--fg-secondary-color);
}
</style>
