<template>
	<div class="flex flex-col gap-4">
		<n-form ref="formRef" :model="formData" :rules label-placement="top">
			<n-form-item label="Check to Exclude" path="check_id">
				<n-select
					v-model:value="formData.check_id"
					placeholder="Select a check"
					:options="checkOptions"
					filterable
				/>
			</n-form-item>

			<n-form-item label="Resource Name (Optional)">
				<n-input
					v-model:value="formData.resource_name"
					placeholder="e.g., specific repository name (leave blank for all)"
				/>
			</n-form-item>

			<n-form-item label="Reason" path="reason">
				<n-input
					v-model:value="formData.reason"
					type="textarea"
					placeholder="Why is this check being excluded?"
					:rows="3"
				/>
			</n-form-item>

			<n-form-item label="Approved By">
				<n-input v-model:value="formData.approved_by" placeholder="Name of approver" />
			</n-form-item>

			<n-form-item label="Expires At">
				<n-date-picker v-model:value="expiresAtTimestamp" type="datetime" clearable />
			</n-form-item>
		</n-form>

		<div class="flex justify-end gap-3">
			<n-button @click="emit('cancel')">Cancel</n-button>
			<n-button type="primary" :loading="saving" @click="handleSubmit">Create</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { FormInst, FormRules } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { GitHubAuditExclusionCreate } from "@/types/github-audit"
import { NButton, NDatePicker, NForm, NFormItem, NInput, NSelect, useMessage } from "naive-ui"
import { onBeforeMount, reactive, ref } from "vue"
import Api from "@/api"
import { useAuthStore } from "@/stores/auth"
import { getApiErrorMessage } from "@/utils"

type ExclusionFormData = Omit<GitHubAuditExclusionCreate, "created_by" | "check_id" | "reason"> & {
	check_id: string | null
	reason: string | null
}

const props = defineProps<{
	configId: number
}>()

const emit = defineEmits<{
	(e: "saved"): void
	(e: "cancel"): void
}>()

const message = useMessage()
const authStore = useAuthStore()
const formRef = ref<FormInst | null>(null)
const saving = ref(false)
const checkOptions = ref<{ label: string; value: string }[]>([])
const expiresAtTimestamp = ref<number | null>(null)

const formData = reactive<ExclusionFormData>({
	check_id: null,
	resource_name: null,
	reason: null,
	approved_by: null,
	expires_at: null
})

const rules: FormRules = {
	check_id: { required: true, message: "Please select a check", trigger: "blur" },
	reason: { required: true, message: "Please provide a reason", trigger: "blur" }
}

async function handleSubmit() {
	try {
		await formRef.value?.validate()
	} catch {
		return
	}

	saving.value = true
	try {
		const data: GitHubAuditExclusionCreate = {
			...formData,
			check_id: formData.check_id ?? "",
			reason: formData.reason ?? "",
			created_by: authStore.userName,
			expires_at: expiresAtTimestamp.value ? new Date(expiresAtTimestamp.value).toISOString() : null
		}
		await Api.githubAudit.createExclusion(props.configId, data)
		message.success("Exclusion created successfully")
		emit("saved")

		formData.check_id = ""
		formData.resource_name = null
		formData.reason = ""
		formData.approved_by = null
		expiresAtTimestamp.value = null
	} catch (error) {
		message.error(getApiErrorMessage(error as ApiError) || "Failed to create exclusion")
	} finally {
		saving.value = false
	}
}

onBeforeMount(async () => {
	try {
		const response = await Api.githubAudit.getAvailableChecks()
		checkOptions.value = response.data.checks.map(check => ({
			label: `${check.name} (${check.severity})`,
			value: check.id
		}))
	} catch (error) {
		console.error("Failed to load available checks:", error)
	}
})
</script>
