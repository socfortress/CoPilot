<template>
	<div class="flex flex-col gap-2">
		<n-card content-class="bg-secondary-color !p-0" class="overflow-hidden" v-if="!showSource">
			<div class="scrollbar-styled overflow-hidden code-bg-transparent" v-shiki="{ lang, decode }">
				<pre v-html="code"></pre>
			</div>
		</n-card>

		<div class="flex justify-end">
			<n-button quaternary size="tiny" @click="showSource = !showSource">toggle source view</n-button>
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
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue"
import { NCard, NInput, NButton } from "naive-ui"
import vShiki from "@/directives/v-shiki"

const { code, lang } = defineProps<{
	code: string | object | number
	lang?: string
	decode?: boolean
}>()

const showSource = ref(false)
const source = computed(() => code.toString())
</script>
