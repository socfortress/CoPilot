<template>
	<!-- Collapsible like every other card in the module: a macro dump or a page of
	     extracted text is long, and folding it away is how you get back to the rest
	     of the tab without scrolling past it. -->
	<CollapsibleCard :default-collapsed :collapsible>
		<template #header>
			<span :class="SECTION_LABEL">{{ title }}</span>
		</template>
		<div class="p-3">
			<CodeSource :code="code || emptyText" :max-height="400" />
		</div>
	</CollapsibleCard>
</template>

<script setup lang="ts">
import CodeSource from "@/components/common/CodeSource.vue"
import CollapsibleCard from "@/components/common/CollapsibleCard.vue"
import { SECTION_LABEL } from "@/components/fileAnalysis/fileAnalysis.helpers"

withDefaults(
	defineProps<{
		title: string
		code?: string
		emptyText?: string
		defaultCollapsed?: boolean
		collapsible?: boolean
	}>(),
	{ code: "", emptyText: "— nothing extracted —", defaultCollapsed: false, collapsible: true }
)
</script>
