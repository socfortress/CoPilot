<template>
	<n-form :disabled="loading" label-placement="top">
		<n-form-item label="Case name" required>
			<n-input v-model:value="model.case_name" placeholder="Insert case name" />
		</n-form-item>
		<n-form-item label="Case description" required>
			<n-input
				v-model:value="model.case_description"
				type="textarea"
				:autosize="{ minRows: 4, maxRows: 8 }"
				placeholder="Insert case description"
			/>
		</n-form-item>
		<n-form-item label="Assigned to (optional)">
			<n-select
				v-model:value="model.assigned_to"
				:options="assignedToOptions"
				:loading="optionsLoading"
				clearable
				filterable
				placeholder="Select assignee"
			/>
		</n-form-item>
		<div class="flex justify-end gap-3">
			<n-button :disabled="loading" @click="emit('cancel')">Cancel</n-button>
			<n-button type="primary" :loading :disabled="!isValidForm" @click="handleSubmit">Create case</n-button>
		</div>
	</n-form>
</template>

<script setup lang="ts">
import type { CasePayload } from "@/api/endpoints/cases"
import type { ApiError } from "@/types/common"
import { NButton, NForm, NFormItem, NInput, NSelect, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"

const emit = defineEmits<{
	(e: "success"): void
	(e: "cancel"): void
}>()

const message = useMessage()
const loading = ref(false)
const optionsLoading = ref(false)
const assignedToOptions = ref<{ label: string; value: string }[]>([])
const model = ref<CasePayload>({
	case_name: "",
	case_description: "",
	assigned_to: undefined
})

const isValidForm = computed(
	() => model.value.case_name.trim().length > 0 && model.value.case_description.trim().length > 0
)

async function loadAssignedToOptions() {
	optionsLoading.value = true

	try {
		const response = await Api.cases.getCasesFilters()
		assignedToOptions.value = response.data.assigned_to.map(o => ({ label: o, value: o }))
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		optionsLoading.value = false
	}
}

async function handleSubmit() {
	if (!isValidForm.value || loading.value) return

	loading.value = true

	try {
		const response = await Api.cases.createCase({
			case_name: model.value.case_name.trim(),
			case_description: model.value.case_description.trim(),
			assigned_to: model.value.assigned_to || undefined
		})
		message.success(response.data.message || "Case created successfully")
		emit("success")
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		loading.value = false
	}
}

onBeforeMount(() => {
	loadAssignedToOptions()
})
</script>
