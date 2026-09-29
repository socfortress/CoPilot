<template>
	<div>
		<vue-markdown-it
			v-if="highlighter"
			:key="languagesVersion"
			:source
			:plugins="[
				[
					fromHighlighter(highlighter, {
						themes: codeThemes,
						fallbackLanguage: MARKDOWN_FALLBACK_LANGUAGE
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
import type { BuiltinLanguage } from "shiki"
import type { HighlighterCore } from "shiki/core"
import { VueMarkdownIt } from "@f3ve/vue-markdown-it"
import { fromHighlighter } from "@shikijs/markdown-it/core"
import { ref, shallowRef, toRefs, watch } from "vue"
import { codeThemes, FALLBACK_LANGUAGE, fencedLanguages, getHighlighter, loadLanguages } from "@/utils/highlighter"
import "@/assets/scss/overrides/vue-md-it-override.scss"

const props = defineProps<{
	source: string
	codeBgTransparent?: boolean
}>()

const emit = defineEmits<{
	(e: "click", value: PointerEvent): void
	(e: "mounted"): void
}>()

const highlighter = shallowRef<HighlighterCore | null>(null)

// A fenced block in a language the highlighter does not carry renders as plain text
// instead of throwing. "text" is shiki's always-available plain language (the plugin's
// own default); the option's type only lists grammar names, hence the cast.
const MARKDOWN_FALLBACK_LANGUAGE = FALLBACK_LANGUAGE as BuiltinLanguage

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
			const target = token.attrs?.[targetIndex]
			if (targetIndex < 0) {
				token.attrPush(["target", "_blank"])
			} else if (target?.[1]) {
				target[1] = "_blank"
			}

			// Aggiungi rel="noopener noreferrer"
			const relIndex = token.attrIndex("rel")
			const rel = token.attrs?.[relIndex]
			if (relIndex < 0) {
				token.attrPush(["rel", "noopener noreferrer"])
			} else if (rel?.[1]) {
				rel[1] = "noopener noreferrer"
			}
		}

		return defaultRender(tokens, idx, options, env, self)
	}
}

const { source, codeBgTransparent } = toRefs(props)

// Rendered once the languages its code blocks name are loaded (and again when the source
// brings new ones): the plugin reads the loaded languages when it renders.
const languagesVersion = ref(0)

watch(
	source,
	async markdown => {
		const instance = highlighter.value ?? (await getHighlighter())
		await loadLanguages(instance, fencedLanguages(markdown))
		const firstRender = !highlighter.value
		highlighter.value = instance
		languagesVersion.value++
		if (firstRender) emit("mounted")
	},
	{ immediate: true }
)
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
