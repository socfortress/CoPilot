<template>
	<!-- Collapsible like every other card in the module: a macro dump or a page of
	     extracted text is long, and folding it away is how you get back to the rest
	     of the tab without scrolling past it. -->
	<CollapsibleCard :default-collapsed :collapsible>
		<template #header>
			<span :class="SECTION_LABEL">{{ title }}</span>
		</template>
		<div class="p-3">
			<!-- A sample's content is its author's: shown as text, never parsed as markup. Long lines
			     wrap, so a one-line obfuscated script can be read without scrolling sideways. -->
			<CodeSource :code="code || emptyText" :lang :max-height="400" text wrap />
		</div>
	</CollapsibleCard>
</template>

<script setup lang="ts">
import CodeSource from "@/components/common/CodeSource.vue"
import CollapsibleCard from "@/components/common/CollapsibleCard.vue"
import { SECTION_LABEL } from "@/components/common/section-label"

withDefaults(
	defineProps<{
		title: string
		code?: string
		/** The highlighter's language; without one it guesses from the start of the code. */
		lang?: string
		emptyText?: string
		defaultCollapsed?: boolean
		collapsible?: boolean
	}>(),
	{ code: "", lang: undefined, emptyText: "— nothing extracted —", defaultCollapsed: false, collapsible: true }
)
</script>
