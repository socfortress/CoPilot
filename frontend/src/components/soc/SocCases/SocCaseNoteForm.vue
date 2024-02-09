<template>
	<n-spin class="soc-notes-form" :show="loading">
		<div class="flex flex-col gap-2">
			<n-input v-model:value="title" placeholder="Title..." clearable />
			<n-input
				v-model:value="content"
				type="textarea"
				clearable
				placeholder="Content..."
				:autosize="{
					minRows: 3,
					maxRows: 10
				}"
			/>
			<div class="flex gap-2 justify-end">
				<n-button :disabled="loading" @click="clear(true)" secondary class="!w-32">Close</n-button>
				<n-button :disabled="loading || !title" @click="addNote()" secondary type="primary" class="!w-32">
					Submit
				</n-button>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import { ref } from "vue"
import Api from "@/api"
import { useMessage, NSpin, NInput, NButton } from "naive-ui"
import type { SocNewNote } from "@/types/soc/note.d"

const { caseId } = defineProps<{ caseId: string | number }>()

const emit = defineEmits<{
	(e: "close"): void
	(e: "added", value: SocNewNote): void
}>()

const loading = ref(false)
const message = useMessage()
const title = ref("")
const content = ref("")

function clear(close?: boolean) {
	title.value = ""
	content.value = ""

	if (close) {
		emit("close")
	}
}

function addNote() {
	loading.value = true

	Api.soc
		.createCaseNote(caseId.toString(), { title: title.value, content: content.value })
		.then(res => {
			if (res.data.success) {
				emit("added", res.data.note)
				clear()
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}
</script>
