<template>
	<div>
		<vue-markdown-it
			v-if="highlighter"
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
		<div v-else>
			{{ source }}
		</div>
	</div>
</template>

<script setup lang="ts">
import type MarkdownIt from "markdown-it/lib/index.mjs"
import type Token from "markdown-it/lib/token.mjs"
import type { HighlighterGeneric } from "shiki/core"
import { VueMarkdownIt } from "@f3ve/vue-markdown-it"
import { fromHighlighter } from "@shikijs/markdown-it/core"
import { onMounted, ref, toRefs } from "vue"
import { codeThemes, getHighlighter } from "@/utils/highlighter"
import "@/assets/scss/overrides/vue-md-it-override.scss"

const props = defineProps<{
	source: string
	codeBgTransparent?: boolean
}>()

const emit = defineEmits<{
	(e: "click", value: PointerEvent): void
	(e: "mounted"): void
}>()

const highlighter = ref<HighlighterGeneric<string, string> | null>(null)

function markdownItLinkTargetBlank(md: MarkdownIt): void {
	const defaultRender =
		md.renderer.rules.link_open ||
		function (tokens: Token[], idx: number, options, _env, self) {
			return self.renderToken(tokens, idx, options)
		}

	md.renderer.rules.link_open = function (tokens: Token[], idx: number, options, env, self) {
		const token = tokens[idx]

		if (token) {
			// Aggiungi target="_blank"
			const targetIndex = token.attrIndex("target")
			if (targetIndex < 0) {
				token.attrPush(["target", "_blank"])
			} else if (token.attrs?.[targetIndex]?.[1]) {
				token.attrs[targetIndex][1] = "_blank"
			}

			// Aggiungi rel="noopener noreferrer"
			const relIndex = token.attrIndex("rel")
			if (relIndex < 0) {
				token.attrPush(["rel", "noopener noreferrer"])
			} else if (token.attrs?.[relIndex]?.[1]) {
				token.attrs[relIndex][1] = "noopener noreferrer"
			}
		}

		return defaultRender(tokens, idx, options, env, self)
	}
}

const { source, codeBgTransparent } = toRefs(props)

onMounted(async () => {
	highlighter.value = (await getHighlighter()) as unknown as HighlighterGeneric<string, string>
	emit("mounted")
})
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
