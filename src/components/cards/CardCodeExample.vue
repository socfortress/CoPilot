<template>
	<n-card class="card">
		<div class="content">
			<div class="description" v-if="$slots.description">
				<slot name="description"></slot>
			</div>
			<slot></slot>
		</div>
		<template #action v-if="$slots.html || $slots.js || $slots.css || $slots.code">
			<n-collapse>
				<template #header-extra>
					<Icon :name="CodeIcon"></Icon>
				</template>
				<n-collapse-item title="Code" name="code">
					<div class="code-container">
						<n-scrollbar x-scrollable style="max-width: 100%; max-height: 400px">
							<slot name="html" v-if="$slots.html"></slot>
							<slot name="js" v-if="$slots.js"></slot>
							<slot name="css" v-if="$slots.css"></slot>
							<slot name="code" :html="html" :js="js" :css="css"></slot>
							<div class="code-box" v-show="loaded.html">
								<div class="label">Template</div>
								<pre ref="refHTML"></pre>
							</div>
							<div class="code-box" v-show="loaded.js">
								<div class="label">Script</div>
								<pre ref="refJS"></pre>
							</div>
							<div class="code-box" v-show="loaded.css">
								<div class="label">Style</div>
								<pre ref="refCSS"></pre>
							</div>
						</n-scrollbar>
					</div>
				</n-collapse-item>
			</n-collapse>
		</template>
	</n-card>
</template>

<script setup lang="ts">
import { hljs, resetIndent } from "@/directives/v-hl"
import { NCollapse, NCollapseItem, NCard, NScrollbar } from "naive-ui"
import { ref } from "vue"
import Icon from "@/components/common/Icon.vue"

type LangType = "html" | "js" | "css"
const CodeIcon = "carbon:code"

const refHTML = ref<HTMLElement | null>(null)
const refJS = ref<HTMLElement | null>(null)
const refCSS = ref<HTMLElement | null>(null)

const loaded = ref({
	html: false,
	js: false,
	css: false
})

function codeInit(code: string, lang: LangType) {
	let el: HTMLElement | null = null
	if (lang === "html") {
		el = refHTML.value
	}
	if (lang === "js") {
		el = refJS.value
	}
	if (lang === "css") {
		el = refCSS.value
	}

	if (el) {
		el.innerHTML = hljs.highlightAuto(code).value
		resetIndent(el)
		loaded.value[lang] = true
	}
}

function html(code: string) {
	if (code) {
		codeInit(code, "html")
	}
}

function js(code: string) {
	if (code) {
		codeInit(code, "js")
	}
}

function css(code: string) {
	if (code) {
		codeInit(code, "css")
	}
}
</script>

<style scoped lang="scss">
.card {
	.content {
		.description {
			line-height: 1.5;
			margin-bottom: 20px;
		}
	}
	.code-container {
		display: grid;

		.code-box {
			margin: 15px 0;

			.label {
				background-color: var(--hover-010-color);
				opacity: 0.5;
				display: inline-block;
				padding: 4px 6px;
				font-size: 12px;
				border-radius: var(--border-radius-small);
				margin-bottom: 5px;
				line-height: 1;
			}
		}
	}
}
</style>
