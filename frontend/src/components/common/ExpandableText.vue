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
			v-shiki="{ fallbackLang: 'json', decode: true }"
			class="expandable-text-popover-container scrollbar-styled"
		>
			<pre> {{ text }} </pre>
		</div>
	</n-popover>
</template>

<script setup lang="ts">
import _truncate from "lodash/truncate"
import { NPopover } from "naive-ui"
import { toRefs } from "vue"
import vShiki from "@/directives/v-shiki"

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
	max-width: 380px;

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
