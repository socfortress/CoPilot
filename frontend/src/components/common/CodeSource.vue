<template>
	<div class="flex flex-col gap-0.5">
		<n-card v-if="!showSource" content-class="p-0!" embedded class="overflow-hidden">
			<!-- Keyed on "Show all": the highlighter reads the block once, when it is created. -->
			<div
				:key="showAll ? 'all' : 'start'"
				v-shiki="{ lang, decode: decode || text }"
				class="scrollbar-styled code-bg-transparent overflow-auto"
				:class="[codeClass, { '[&_pre]:wrap-anywhere [&_pre]:whitespace-pre-wrap': wrap }]"
				:style="codeBlockStyle"
			>
				<!-- `text`: the code is plain text, so it is never parsed as HTML (a `<placeholder>` stays one).
				     Until it is highlighted, or when it is too large to be, it looks like highlighted code. -->
				<pre v-if="text" class="p-3 text-[13px]">{{ shown.text }}</pre>
				<pre v-else class="p-3 text-[13px]" v-html="shown.text"></pre>
			</div>
		</n-card>

		<div
			v-if="!showSource && shown.hidden"
			class="text-secondary flex flex-wrap items-center justify-between gap-2 text-xs"
			data-testid="code-source-cut"
		>
			<span>
				Showing the first {{ count(shown.text.length) }} of {{ count(source.length) }} characters.
			</span>
			<n-button quaternary size="tiny" @click="showAll = true">Show all</n-button>
		</div>

		<n-input
			v-if="showSource"
			:value="source"
			type="textarea"
			readonly
			placeholder="Empty"
			size="large"
			:autosize="{
				minRows: 3,
				maxRows: 18
			}"
		/>

		<div v-if="showToggleButton" class="flex items-center justify-end gap-2">
			<n-button v-if="isSupported" quaternary size="tiny" @click="copy(source)">
				<template #icon>
					<Icon name="carbon:copy" :size="12" />
				</template>
				{{ copied ? "copied!" : "copy source" }}
			</n-button>

			<n-button quaternary size="tiny" @click="showSource = !showSource">
				<template #icon>
					<Icon name="carbon:code" :size="14" />
				</template>
				toggle source view
			</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { HTMLAttributes } from "vue"
import { useClipboard } from "@vueuse/core"
import { NButton, NCard, NInput } from "naive-ui"
import { computed, ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import vShiki from "@/directives/v-shiki"
import { shownCode } from "@/utils/code-highlight"

const {
	code,
	lang,
	decode,
	text = false,
	showToggleButton = true,
	maxHeight,
	codeClass,
	wrap = false
} = defineProps<{
	code: string | object | number
	lang?: string
	decode?: boolean
	/**
	 * The code is plain text (a shell command with `<placeholders>`, a log line): shown as text, never
	 * parsed as HTML, and copied as written. Without it the code is rendered as HTML, as before.
	 */
	text?: boolean
	showToggleButton?: boolean
	maxHeight?: string | number
	codeClass?: HTMLAttributes["class"]
	/** Wrap long lines instead of scrolling sideways (a one-line obfuscated script reads better wrapped). */
	wrap?: boolean
}>()

const { copy, copied, isSupported } = useClipboard()

const showSource = ref(false)
const source = computed(() =>
	typeof code === "string" || typeof code === "number" ? `${code}` : JSON.stringify(code, null, "\t")
)

/** A very large block shows its start until "Show all" (#1360); copying always takes everything. */
const showAll = ref(false)
const shown = computed(() => shownCode(source.value, showAll.value))

function count(n: number): string {
	return n.toLocaleString("en-US")
}

const codeBlockStyle = computed(() => {
	if (maxHeight == null) return undefined
	return { maxHeight: typeof maxHeight === "number" ? `${maxHeight}px` : maxHeight }
})
</script>
