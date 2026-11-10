<template>
	<!-- Marks where the bar sits in the flow: its scroll timeline drives the backdrop (see the style). -->
	<div class="knowledge-nav-sentinel" aria-hidden="true" />
	<nav
		ref="nav"
		class="knowledge-nav"
		:class="{ 'in-overlay': inOverlay }"
		aria-label="Knowledge sections"
		data-testid="knowledge-nav"
	>
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

const nav = ref<HTMLElement | null>(null)
const track = ref<HTMLElement | null>(null)

// Under the app's toolbar only on the customer's own page, where both share a scroller. In a modal
// nothing sits above the bar: it sticks to the top and draws no backdrop.
const inOverlay = ref(false)

onMounted(() => {
	const page = document.querySelector("header.toolbar")?.closest(".n-scrollbar-container")
	inOverlay.value = !nav.value || !page?.contains(nav.value)
	emit("ready")
})

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
// The bar sticks below the app's toolbar. That toolbar is see-through, so as the bar nears it a
// backdrop grows from the bar's top edge up to the top of the page, its edge scrolling with the
// facts as if the bar's top kept going: the facts never show behind the toolbar above the bar.
// The growth is a scroll-driven transform, run by the browser in step with the scroll (a script
// setting it on every scroll event lagged a frame behind and shook). Without scroll-driven
// animations the bar simply has no backdrop.
.knowledge-nav-sentinel {
	position: absolute;
	height: 0;
	view-timeline: --knowledge-nav-approach block;
}

.knowledge-nav {
	position: sticky;
	top: var(--toolbar-height);
	z-index: 2;
	margin: 0 -16px;
	padding: 8px 16px;
	background-color: var(--bg-body-color);
	border-bottom: 1px solid var(--border-color);

	&.in-overlay {
		top: 0;
	}
}

@supports (animation-timeline: view()) {
	.knowledge-nav:not(.in-overlay)::before {
		content: "";
		position: absolute;
		inset-inline: 0;
		bottom: 100%;
		height: var(--toolbar-height);
		background-color: var(--bg-body-color);
		pointer-events: none;
		transform-origin: bottom;
		animation: knowledge-nav-backdrop linear both;
		animation-timeline: --knowledge-nav-approach;
		// From the bar's place in the flow a toolbar's height below the top of the page, to the top.
		animation-range: cover calc(100% - var(--toolbar-height)) cover 100%;
	}
}

@keyframes knowledge-nav-backdrop {
	from {
		transform: scaleY(0);
	}
	to {
		transform: scaleY(1);
	}
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
