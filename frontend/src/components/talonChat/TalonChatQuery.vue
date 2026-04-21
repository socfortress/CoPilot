<template>
	<div class="relative flex flex-col overflow-hidden">
		<div
			v-if="!!editMessageBody"
			class="bg-secondary hover:text-primary mb-2 flex cursor-pointer items-center gap-2 rounded-lg px-2 py-2 text-sm transition-colors duration-200"
			@click="handleCancelEdit()"
		>
			<Icon name="carbon:close" :size="20" />
			<div>Edit message</div>
		</div>
		<n-input
			v-model:value.trim="input"
			class="max-h-full min-h-20 pt-1 pb-9"
			type="textarea"
			placeholder="Ask Talon..."
			:autosize="{
				minRows: 3,
				maxRows: 18
			}"
		/>
		<div class="absolute right-0 bottom-0 left-0 flex items-center justify-between p-2 pr-3">
			<div class="flex items-center gap-2.5">
				<n-button size="tiny" secondary @click="clearChat()">
					<template #icon>
						<Icon name="mdi:broom" />
					</template>
					Clear chat
				</n-button>
			</div>
			<n-button
				circle
				size="small"
				secondary
				:type="isFormValid ? 'primary' : undefined"
				:disabled="!isFormValid && !loading"
				@click="loading ? stop() : send()"
			>
				<Icon :name="loading ? 'carbon:stop-filled-alt' : 'carbon:arrow-up'" />
			</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import _trim from "lodash/trim"
import { NButton, NInput } from "naive-ui"
import { computed, toRefs } from "vue"
import Icon from "@/components/common/Icon.vue"

export interface Message {
	input: string
}

const props = defineProps<{ loading?: boolean; editMessageBody?: string | null }>()

const emit = defineEmits<{
	(e: "message", value: Message): void
	(e: "stop"): void
	(e: "cancel-edit"): void
	(e: "clear-chat"): void
}>()

const { loading, editMessageBody } = toRefs(props)
const input = defineModel<string | null>("input", { default: null })
const isFormValid = computed(() => !!_trim(input.value || ""))

function reset() {
	input.value = null
}

function send() {
	if (input.value) {
		emit("message", {
			input: input.value
		})

		reset()
	}
}

function stop() {
	emit("stop")
}

function handleCancelEdit() {
	emit("cancel-edit")
	reset()
}

function clearChat() {
	emit("clear-chat")
}
</script>
