<template>
	<div class="flex flex-col gap-2">
		<n-card v-if="!showSource" content-class="bg-secondary-color !p-0" class="overflow-hidden">
			<div v-shiki="{ lang, decode }" class="scrollbar-styled overflow-hidden code-bg-transparent">
				<pre v-html="source"></pre>
			</div>
		</n-card>

		<div class="flex justify-end">
			<n-button quaternary size="tiny" @click="showSource = !showSource">
				toggle source view
			</n-button>
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
				maxRows: 18,
			}"
		/>
	</div>
</template>

<script setup lang="ts">
import vShiki from "@/directives/v-shiki"
import { NButton, NCard, NInput } from "naive-ui"
import { computed, ref } from "vue"

const { code, lang } = defineProps<{
	code: string | object | number
	lang?: string
	decode?: boolean
}>()

const showSource = ref(false)
const source = computed(() => JSON.stringify(code, null, "\t"))
</script>
