<template>
	<n-button quaternary class="w-full! justify-start!" @click="showModal = true">
		<template #icon>
			<Icon :name="RoleIcon" :size="14" />
		</template>
		Assign Role
	</n-button>

	<n-modal
		v-model:show="showModal"
		display-directive="show"
		preset="card"
		:style="{ maxWidth: 'min(500px, 90vw)', minHeight: 'min(200px, 50vh)' }"
		title="Assign Role"
		:bordered="false"
		content-class="flex flex-col"
		segmented
	>
		<div class="flex flex-col gap-4">
			<div>
				<strong>User:</strong>
				{{ user?.username }}
			</div>

			<n-form ref="formRef" :model="formModel" :rules="rules">
				<n-form-item path="role" label="Select Role">
					<n-select
						v-model:value="formModel.role"
						:options="roleOptions"
						placeholder="Choose a role"
						:loading="loading"
					/>
				</n-form-item>
			</n-form>

			<div class="flex justify-end gap-3">
				<n-button @click="showModal = false">Cancel</n-button>
				<n-button type="primary" :loading="loading" :disabled="!formModel.role" @click="handleAssignRole">
					Assign Role
				</n-button>
			</div>
		</div>
	</n-modal>
</template>

<script setup lang="ts">
import type { FormInst } from "naive-ui"
import type { User } from "@/types/user.d"
import { NButton, NForm, NFormItem, NModal, NSelect, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
	user?: User
}>()

const emit = defineEmits<{
	success: []
}>()

const RoleIcon = "carbon:user-role"
const message = useMessage()
const showModal = ref(false)
const loading = ref(false)
const formRef = ref<FormInst>()

const formModel = ref({
	role: null as string | null
})

const roleOptions = [
	{ label: "Admin", value: "admin" },
	{ label: "Analyst", value: "analyst" },
	{ label: "Scheduler", value: "scheduler" },
	{ label: "Customer User", value: "customer_user" }
]

const rules = {
	role: {
		required: true,
		message: "Please select a role",
		trigger: ["blur", "change"]
	}
}

function handleAssignRole() {
	if (!props.user || !formModel.value.role) return

	formRef.value?.validate(async errors => {
		if (!errors && props.user?.id && formModel.value.role) {
			loading.value = true

			try {
				const res = await Api.auth.assignRole(props.user.id, formModel.value.role)
				if (res.data.success) {
					message.success(res.data.message || "Role assigned successfully")
					showModal.value = false
					formModel.value.role = null
					emit("success")
				} else {
					message.error(res.data.message || "Failed to assign role")
				}
			} catch (err: any) {
				message.error(err.response?.data?.message || "Failed to assign role")
			} finally {
				loading.value = false
			}
		}
	})
}
</script>
