<template>
	<div class="blur-gradient relative">
		<BlurEffect class="rotate-180" />

		<n-scrollbar
			x-scrollable
			class="max-w-full"
			trigger="none"
			:theme-overrides="{
				railInsetHorizontalBottom: `auto 16px 4px 16px`
			}"
		>
			<div class="flex items-end gap-4 p-4">
				<ChatQuestion
					v-for="item of selectedExampleQuestions"
					:key="item.question"
					:entity="item"
					@click="emit('select', item.question)"
				/>
			</div>
		</n-scrollbar>
	</div>
</template>

<script setup lang="ts">
import type { ExampleQuestion } from "@/types/copilotMCP.d"
import { NScrollbar, useMessage } from "naive-ui"
import { computed, ref, toRefs, watch } from "vue"
import Api from "@/api"
import BlurEffect from "@/components/common/BlurEffect.vue"
import ChatQuestion from "./ChatQuestion.vue"

const props = defineProps<{ server: string }>()

const emit = defineEmits<{
	(e: "select", value: string): void
}>()

const { server } = toRefs(props)

const loadingExampleQuestions = ref(false)
const message = useMessage()
const exampleQuestions = ref<{ server: string; questions: ExampleQuestion[] }[]>([])

const selectedExampleQuestions = computed<ExampleQuestion[]>(
	() => exampleQuestions.value.find(o => o.server === server.value)?.questions || []
)

function isServerExamplesFilled(server: string) {
	return !!exampleQuestions.value.find(o => o.server === server)?.questions.length
}

function getExampleQuestions(server: string) {
	if (isServerExamplesFilled(server)) {
		return
	}

	loadingExampleQuestions.value = true

	Api.copilotMCP
		.getExampleQuestions(server)
		.then(res => {
			if (res.data.success) {
				upsertExampleQuestions(server, res.data.questions)
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingExampleQuestions.value = false
		})
}

function upsertExampleQuestions(server: string, questions: ExampleQuestion[]) {
	if (!exampleQuestions.value.find(o => o.server === server)) {
		exampleQuestions.value.push({
			server,
			questions
		})
	}
}

watch(
	server,
	val => {
		if (val) {
			getExampleQuestions(val)
		}
	},
	{ immediate: true }
)
</script>

<style lang="scss" scoped>
.blur-gradient {
	background: linear-gradient(to top, var(--bg-default-color) 0%, var(--bg-default-color) 20%, transparent 100%);
}
</style>
