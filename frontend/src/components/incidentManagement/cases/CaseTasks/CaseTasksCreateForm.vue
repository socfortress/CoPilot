<template>
	<n-form ref="addFormRef" :model="addForm" :rules="addFormRules" label-placement="top" :disabled="submitting">
		<n-form-item label="Title" path="title">
			<n-input v-model:value="addForm.title" placeholder="What needs to be done?" />
		</n-form-item>
		<n-form-item path="mandatory" :show-label="false">
			<n-checkbox v-model:checked="addForm.mandatory">Mandatory (blocks close-with-warning)</n-checkbox>
		</n-form-item>
		<n-form-item label="Description (optional)" path="description">
			<n-input v-model:value="addForm.description" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" />
		</n-form-item>
		<n-form-item label="Guidelines (optional)" path="guidelines">
			<n-input
				v-model:value="addForm.guidelines"
				type="textarea"
				placeholder="Best practices / steps to follow"
				:autosize="{ minRows: 2, maxRows: 6 }"
			/>
		</n-form-item>
		<div class="flex justify-end gap-2">
			<n-button type="primary" :loading="submitting" :disabled="!isValid" @click="submitAddTask">
				Add task
			</n-button>
		</div>
	</n-form>
</template>

<script setup lang="ts">
import type { FormInst, FormRules } from "naive-ui"
import type { ApiError } from "@/types/common"
import { NButton, NCheckbox, NForm, NFormItem, NInput, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"

const { caseId } = defineProps<{
	caseId: number
}>()

const emit = defineEmits<{
	(e: "success"): void
}>()

const message = useMessage()

const submitting = ref(false)
const addFormRef = ref<FormInst | null>(null)
const addForm = ref({
	title: "",
	description: "",
	guidelines: "",
	mandatory: false
})

const addFormRules: FormRules = {
	title: { required: true, message: "Title is required", trigger: "blur" }
}

const isValid = computed(() => {
	return addForm.value.title.trim() !== ""
})

function resetForm() {
	addForm.value = { title: "", description: "", guidelines: "", mandatory: false }
}

async function submitAddTask() {
	try {
		await addFormRef.value?.validate()
	} catch {
		return
	}
	submitting.value = true

	try {
		const res = await Api.incidentManagement.caseTemplates.addCaseTask(caseId, {
			title: addForm.value.title,
			description: addForm.value.description || null,
			guidelines: addForm.value.guidelines || null,
			mandatory: addForm.value.mandatory
		})
		if (res.data.success && res.data.task) {
			resetForm()
			emit("success")
		} else {
			message.warning(res.data.message)
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to add task")
	} finally {
		submitting.value = false
	}
}
</script>
