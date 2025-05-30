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
			<div class="flex justify-end gap-2">
				<n-button :disabled="loading" secondary class="!w-32" @click="clear(true)">Close</n-button>
				<n-button :disabled="loading || !title" secondary type="primary" class="!w-32" @click="addNote()">
					Submit
				</n-button>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { SocNewNote } from "@/types/soc/note.d"
import { NButton, NInput, NSpin, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"

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
