<template>
	<div class="flex flex-col gap-2">
		<n-card v-if="!showSource" content-class="!p-0" embedded class="overflow-hidden">
			<div v-shiki="{ lang, decode }" class="scrollbar-styled code-bg-transparent overflow-hidden">
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

		<div v-if="showToggleButton" class="flex justify-end">
			<n-button quaternary size="tiny" @click="showSource = !showSource">toggle source view</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { NButton, NCard, NInput } from "naive-ui"
import { computed, ref } from "vue"
import vShiki from "@/directives/v-shiki"

const {
	code,
	lang,
	decode,
	showToggleButton = true
} = defineProps<{
	code: string | object | number
	lang?: string
	decode?: boolean
	showToggleButton?: boolean
}>()

const showSource = ref(false)
const source = computed(() =>
	typeof code === "string" || typeof code === "number" ? `${code}` : JSON.stringify(code, null, "\t")
)
</script>
