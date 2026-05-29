<template>
	<div class="flex flex-col gap-0.5">
		<n-card v-if="!showSource" content-class="p-0!" embedded class="overflow-hidden">
			<div
				v-shiki="{ lang, decode }"
				class="scrollbar-styled code-bg-transparent overflow-auto"
				:class="codeClass"
				:style="codeBlockStyle"
			>
				<pre v-html="source"></pre>
			</div>
		</n-card>

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

const {
	code,
	lang,
	decode,
	showToggleButton = true,
	maxHeight,
	codeClass
} = defineProps<{
	code: string | object | number
	lang?: string
	decode?: boolean
	showToggleButton?: boolean
	maxHeight?: string | number
	codeClass?: HTMLAttributes["class"]
}>()

const { copy, copied, isSupported } = useClipboard()

const showSource = ref(false)
const source = computed(() =>
	typeof code === "string" || typeof code === "number" ? `${code}` : JSON.stringify(code, null, "\t")
)

const codeBlockStyle = computed(() => {
	if (maxHeight == null) return undefined
	return { maxHeight: typeof maxHeight === "number" ? `${maxHeight}px` : maxHeight }
})
</script>
