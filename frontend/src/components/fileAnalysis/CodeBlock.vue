<template>
	<div class="code-block bg-secondary flex flex-col overflow-hidden rounded-lg">
		<div class="border-default flex items-center justify-between gap-2 border-b px-3 py-2">
			<span class="text-secondary text-xs font-medium">{{ title }}</span>
			<n-button size="tiny" quaternary :disabled="!code" @click="copy()">
				<template #icon>
					<Icon :name="CopyIcon" :size="14" />
				</template>
				Copy
			</n-button>
		</div>
		<n-scrollbar x-scrollable class="max-h-100">
			<pre class="px-3 py-2 font-mono text-xs leading-relaxed whitespace-pre">{{ code || emptyText }}</pre>
		</n-scrollbar>
	</div>
</template>

<script setup lang="ts">
import { NButton, NScrollbar, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

const props = withDefaults(
	defineProps<{
		title: string
		code?: string
		emptyText?: string
	}>(),
	{ code: "", emptyText: "— nothing extracted —" }
)

const message = useMessage()
const CopyIcon = "carbon:copy"

// Display-only. This text is attacker-controlled (extracted from the sample) and
// is rendered as inert text — never evaluated, never injected as HTML.
function copy() {
	if (!props.code) return
	navigator.clipboard
		.writeText(props.code)
		.then(() => message.success("Copied to clipboard"))
		.catch(() => message.error("Copy failed"))
}
</script>
