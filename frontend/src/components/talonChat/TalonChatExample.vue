<template>
	<div class="text-secondary flex flex-col items-center justify-center text-center">
		<Icon name="carbon:chat-bot" :size="40" class="text-tertiary mb-3" />
		<p class="text-lg font-semibold">Welcome to Talon AI</p>
		<p class="text-tertiary mt-1 max-w-md text-sm">
			Your AI-powered security analyst. Ask questions about alerts, threats, or your environment and Talon will
			investigate and respond.
		</p>
		<div class="mt-6 flex flex-col gap-2">
			<n-button
				v-for="example of exampleMessages"
				:key="example"
				size="large"
				secondary
				@click="useExample(example)"
			>
				{{ example }}
			</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { NButton } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

const emit = defineEmits<{
	(e: "example", value: string): void
}>()

const exampleMessages = [
	"Summarize the most critical alerts from today",
	"What MITRE ATT&CK techniques have been seen this week?",
	"Explain what a brute force attack looks like in our logs",
	"What should I investigate first as a SOC analyst?"
]

function useExample(example: string) {
	emit("example", example)
}
</script>
