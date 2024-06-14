<template>
	<Suspense>
		<vue-markdown-it
			:source="source"
			preset="commonmark"
			:plugins="[
				[
					fromHighlighter(highlighter, {
						themes: codeThemes
					})
				]
			]"
			class="markdown-style scrollbar-styled"
			:class="{ codeBgTransparent }"
		/>
	</Suspense>
</template>

<script setup lang="ts">
import { toRefs } from "vue"
import { VueMarkdownIt } from "@f3ve/vue-markdown-it"
import { getHighlighter, codeThemes } from "@/utils/highlighter"
import { fromHighlighter } from "@shikijs/markdown-it/core"
import type { HighlighterGeneric } from "shiki/core"

const highlighter: HighlighterGeneric<string, string> = (await getHighlighter()) as unknown as HighlighterGeneric<
	string,
	string
>

const props = defineProps<{
	source: string
	codeBgTransparent?: boolean
}>()
const { source, codeBgTransparent } = toRefs(props)
</script>

<style lang="scss" scoped>
.markdown-style {
	:deep() {
		& > * {
			margin-bottom: 15px;
		}
	}

	&.codeBgTransparent {
		:deep() {
			& > pre {
				& > code {
					background-color: transparent;
				}
			}
		}
	}
}
</style>
