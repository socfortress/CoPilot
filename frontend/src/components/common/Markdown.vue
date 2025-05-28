<template>
	<Suspense>
		<vue-markdown-it
			:source
			:plugins="[
				[
					fromHighlighter(highlighter, {
						themes: codeThemes
					})
				],
				markdownItLinkTargetBlank
			]"
			class="markdown-style scrollbar-styled"
			:class="{ 'code-bg-transparent': codeBgTransparent }"
			@click="emit('click', $event)"
		/>
	</Suspense>
</template>

<script setup lang="ts">
import type MarkdownIt from "markdown-it/lib/index.mjs"
import type Token from "markdown-it/lib/token.mjs"
import type { HighlighterGeneric } from "shiki/core"
import { VueMarkdownIt } from "@f3ve/vue-markdown-it"
import { fromHighlighter } from "@shikijs/markdown-it/core"
import { toRefs } from "vue"
import { codeThemes, getHighlighter } from "@/utils/highlighter"
import "@/assets/scss/overrides/vue-md-it-override.scss"

const props = defineProps<{
	source: string
	codeBgTransparent?: boolean
}>()

const emit = defineEmits<{
	(e: "click", value: PointerEvent): void
}>()

const highlighter: HighlighterGeneric<string, string> = (await getHighlighter()) as unknown as HighlighterGeneric<
	string,
	string
>

function markdownItLinkTargetBlank(md: MarkdownIt): void {
	const defaultRender =
		md.renderer.rules.link_open ||
		function (tokens: Token[], idx: number, options, _env, self) {
			return self.renderToken(tokens, idx, options)
		}

	md.renderer.rules.link_open = function (tokens: Token[], idx: number, options, env, self) {
		const token = tokens[idx]

		// Aggiungi target="_blank"
		const targetIndex = token.attrIndex("target")
		if (targetIndex < 0) {
			token.attrPush(["target", "_blank"])
		} else {
			token.attrs![targetIndex][1] = "_blank"
		}

		// Aggiungi rel="noopener noreferrer"
		const relIndex = token.attrIndex("rel")
		if (relIndex < 0) {
			token.attrPush(["rel", "noopener noreferrer"])
		} else {
			token.attrs![relIndex][1] = "noopener noreferrer"
		}

		return defaultRender(tokens, idx, options, env, self)
	}
}

const { source, codeBgTransparent } = toRefs(props)
</script>

<style lang="scss" scoped>
.markdown-style {
	:deep() {
		& > * {
			margin-bottom: 15px;
		}
	}

	&.code-bg-transparent {
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
