<template>
	<n-popover
		placement="top"
		content-class="expandable-text-popover"
		scrollable
		to="body"
		display-directive="show"
		:disabled="text.length < maxLength"
	>
		<template #trigger>
			<span v-if="text.length < maxLength">{{ text }}</span>
			<span v-else class="cursor-help underline">{{ truncate(text) }}</span>
		</template>

		<div
			class="expandable-text-popover-container scrollbar-styled"
			v-shiki="{ fallbackLang: 'json', decode: true }"
		>
			<pre> {{ text }} </pre>
		</div>
	</n-popover>
</template>

<script setup lang="ts">
import vShiki from "@/directives/v-shiki"
import { toRefs } from "vue"
import { NPopover } from "naive-ui"
import _truncate from "lodash/truncate"

const props = defineProps<{
	text: string
	maxLength: number
}>()
const { text, maxLength } = toRefs(props)

function truncate(val: string): string {
	return _truncate(val || "", {
		length: maxLength.value
	})
}
</script>

<style lang="scss">
.expandable-text-popover {
	@apply max-w-96;

	.expandable-text-popover-container {
		overflow-x: hidden;
		overflow-y: auto;
		max-height: 40svh;

		pre {
			white-space: pre-wrap;

			code {
				overflow: hidden;
				white-space: pre-wrap;
				background-color: transparent !important;
			}
		}
	}
}
</style>
