<template>
	<vue-markdown-it
		:source="source"
		preset="commonmark"
		:plugins="[[markdownItHighlightjs, { hljs, auto: true, code: true, inline: false, ignoreIllegals: true }]]"
		class="markdown-style scrollbar-styled"
	/>
</template>

<script setup lang="ts">
import { toRefs } from "vue"
import markdownItHighlightjs from "markdown-it-highlightjs/core"
import "@/assets/scss/hljs.scss"
import { VueMarkdownIt } from "@f3ve/vue-markdown-it"

import hljs from "highlight.js/lib/core"
import powershell from "highlight.js/lib/languages/powershell"
import bash from "highlight.js/lib/languages/bash"
import json from "highlight.js/lib/languages/json"
import xml from "highlight.js/lib/languages/xml"

hljs.registerLanguage("powershell", powershell)
hljs.registerLanguage("bash", bash)
hljs.registerLanguage("json", json)
hljs.registerLanguage("xml", xml)

const props = defineProps<{
	source: string
}>()
const { source } = toRefs(props)
</script>

<style lang="scss" scoped>
.markdown-style {
	:deep() {
		& > * {
			margin-bottom: 15px;
		}
	}
}
</style>
