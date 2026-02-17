<template>
	<n-modal v-model:show="showModal" preset="dialog" title="Add Exclusion" style="width: 500px">
		<n-form ref="formRef" :model="formData" :rules="rules" label-placement="top">
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

		<template #action>
			<n-button @click="showModal = false">Cancel</n-button>
			<n-button type="primary" :loading="saving" @click="handleSubmit">Create</n-button>
		</template>
	</n-modal>
</template>

<script setup lang="ts">
// TODO: refactor
import type { FormInst, FormRules } from "naive-ui"
import type { GitHubAuditExclusionCreate } from "@/types/githubAudit.d"
import { NButton, NDatePicker, NForm, NFormItem, NInput, NModal, NSelect, useMessage } from "naive-ui"
import { computed, onMounted, reactive, ref } from "vue"
import Api from "@/api"

const props = defineProps<{
	show: boolean
	configId: number
}>()

const emit = defineEmits<{
	(e: "update:show", value: boolean): void
	(e: "saved"): void
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const saving = ref(false)
const checkOptions = ref<{ label: string; value: string }[]>([])
const expiresAtTimestamp = ref<number | null>(null)

const showModal = computed({
	get: () => props.show,
	set: value => emit("update:show", value)
})

const formData = reactive<GitHubAuditExclusionCreate>({
	check_id: "",
	resource_name: null,
	reason: "",
	approved_by: null,
	expires_at: null,
	created_by: "current_user" // TODO: Get from auth context
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
		const data = {
			...formData,
			expires_at: expiresAtTimestamp.value ? new Date(expiresAtTimestamp.value).toISOString() : null
		}
		await Api.githubAudit.createExclusion(props.configId, data)
		message.success("Exclusion created successfully")
		emit("saved")
		showModal.value = false

		// Reset form
		formData.check_id = ""
		formData.resource_name = null
		formData.reason = ""
		formData.approved_by = null
		expiresAtTimestamp.value = null
	} catch (error: any) {
		message.error(error.response?.data?.detail || "Failed to create exclusion")
	} finally {
		saving.value = false
	}
}

onMounted(async () => {
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
