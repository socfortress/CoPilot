<template>
	<div>
		<vue-markdown-it
			v-if="highlighter"
			:source
			:options="mdOptions"
			:plugins
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
import { computed, onMounted, ref, toRefs } from "vue"
import { codeThemes, getHighlighter, markdownItNoImages, markdownItSafeHighlight } from "@/utils/highlighter"
import "@/assets/scss/overrides/vue-md-it-override.scss"

const props = defineProps<{
	source: string
	codeBgTransparent?: boolean
	breaks?: boolean
	/** Render `![x](url)` as a link, never as an image that loads (Talon's v2 chat). */
	noImages?: boolean
}>()

const emit = defineEmits<{
	(e: "click", value: PointerEvent): void
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

const { source, codeBgTransparent, breaks, noImages } = toRefs(props)

const plugins = computed(() => {
	if (!highlighter.value) return []
	return [
		[fromHighlighter(highlighter.value, { themes: codeThemes })],
		// After Shiki's: a language it hasn't loaded must never blank the document.
		markdownItSafeHighlight(highlighter.value),
		markdownItLinkTargetBlank,
		...(noImages.value ? [markdownItNoImages] : [])
	]
})

const mdOptions = computed(() => ({
	...(breaks.value ? { breaks: true } : {})
}))

onMounted(async () => {
	highlighter.value = (await getHighlighter()) as unknown as HighlighterGeneric<string, string>
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
