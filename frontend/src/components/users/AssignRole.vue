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

			<n-form ref="formRef" :model="formModel" :rules>
				<n-form-item path="role" label="Select Role">
					<n-select
						v-model:value="formModel.role"
						:options="ROLE_NAME_OPTIONS"
						placeholder="Choose a role"
						:loading
						data-testid="assign-role-select"
					/>
				</n-form-item>
				<!-- An analyst or responder sees only their customers: they are chosen with the role (#1219). -->
				<n-form-item v-if="customersNeeded" label="Customers" :feedback="NEEDS_A_CUSTOMER">
					<UserCustomersSelect v-model:value="formModel.customerCodes" />
				</n-form-item>
			</n-form>

			<div class="flex justify-end gap-3">
				<n-button @click="showModal = false">Cancel</n-button>
				<n-button
					type="primary"
					:loading
					:disabled="!canAssign"
					data-testid="assign-role-submit"
					@click="handleAssignRole"
				>
					Assign Role
				</n-button>
			</div>
		</div>
	</n-modal>
</template>

<script setup lang="ts">
import type { FormInst } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { User } from "@/types/user"
import { NButton, NForm, NFormItem, NModal, NSelect, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import { NEEDS_A_CUSTOMER, needsCustomers, ROLE_NAME_OPTIONS } from "./roles"

const props = defineProps<{
	user?: User
}>()

const emit = defineEmits<{
	success: []
}>()

const UserCustomersSelect = defineAsyncComponent(() => import("./UserCustomersSelect.vue"))

const RoleIcon = "carbon:user-role"
const message = useMessage()
const showModal = ref(false)
const loading = ref(false)
const formRef = ref<FormInst>()

const formModel = ref({
	role: null as string | null,
	customerCodes: [] as string[]
})

const customersNeeded = computed(() => needsCustomers(formModel.value.role))
const canAssign = computed(
	() => !!formModel.value.role && (!customersNeeded.value || formModel.value.customerCodes.length > 0)
)

const rules = {
	role: {
		required: true,
		message: "Please select a role",
		trigger: ["blur", "change"]
	}
}

// Start from the user's current customers, so promoting an analyst keeps theirs.
async function loadCustomers() {
	formModel.value.customerCodes = []
	if (!props.user) return
	try {
		const res = await Api.auth.getUserCustomerAccess(props.user.id)
		if (res.data.success) formModel.value.customerCodes = [...(res.data.customer_codes || [])]
	} catch {
		// the select starts empty and the user picks them
	}
}

watch(showModal, open => {
	if (open) loadCustomers()
})

function handleAssignRole() {
	if (!props.user || !formModel.value.role) return

	formRef.value?.validate(async errors => {
		if (!errors && props.user?.id && formModel.value.role && canAssign.value) {
			loading.value = true

			try {
				const customerCodes = customersNeeded.value ? formModel.value.customerCodes : undefined
				const res = await Api.auth.assignRole(props.user.id, formModel.value.role, customerCodes)
				if (res.data.success) {
					message.success(res.data.message || "Role assigned successfully")
					showModal.value = false
					formModel.value.role = null
					emit("success")
				} else {
					message.error(res.data.message || "Failed to assign role")
				}
			} catch (err) {
				message.error(getApiErrorMessage(err as ApiError) || "Failed to assign role")
			} finally {
				loading.value = false
			}
		}
	})
}
</script>
