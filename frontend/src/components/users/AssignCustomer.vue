<template>
	<n-button quaternary class="w-full! justify-start!" @click="showModal = true">
		<template #icon>
			<Icon :name="CustomerIcon" :size="14" />
		</template>
		Assign Customer
	</n-button>

	<n-modal
		v-model:show="showModal"
		display-directive="show"
		preset="card"
		:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(300px, 60vh)' }"
		title="Assign Customer Access"
		:bordered="false"
		content-class="flex flex-col"
		segmented
	>
		<div class="flex flex-col gap-4">
			<div>
				<strong>User:</strong>
				{{ user?.username }}
			</div>

			<n-form :model="formModel">
				<n-form-item label="Select Customers">
					<n-select
						v-model:value="formModel.customerCodes"
						:options="customerOptions"
						placeholder="Choose customers"
						multiple
						:loading="loadingCustomers"
					/>
				</n-form-item>

				<n-form-item label="Current Access">
					<div v-if="currentAccess.length > 0" class="flex flex-wrap gap-2">
						<n-tag v-for="customerCode in currentAccess" :key="customerCode" type="info" size="small">
							{{ customerCode }}
						</n-tag>
					</div>
					<div v-else class="text-gray-500">No customer access assigned</div>
				</n-form-item>
			</n-form>

			<div class="flex justify-end gap-3">
				<n-button @click="showModal = false">Cancel</n-button>
				<n-button type="primary" :loading @click="handleAssignCustomers">Assign Customers</n-button>
			</div>
		</div>
	</n-modal>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { Customer } from "@/types/customers"
import type { User } from "@/types/user"
import { NButton, NForm, NFormItem, NModal, NSelect, NTag, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	user?: User
}>()

const emit = defineEmits<{
	success: []
}>()

const CustomerIcon = "carbon:user-certification"
const message = useMessage()
const showModal = ref(false)
const loading = ref(false)
const loadingCustomers = ref(false)
const customers = ref<Customer[]>([])
const currentAccess = ref<string[]>([])

const formModel = ref({
	customerCodes: [] as string[]
})

const customerOptions = computed(() =>
	customers.value.map(customer => ({
		label: `${customer.customer_name} (${customer.customer_code})`,
		value: customer.customer_code
	}))
)

async function loadCustomers() {
	loadingCustomers.value = true
	try {
		const res = await Api.customers.getCustomers()
		if (res.data.success && res.data.customers) {
			customers.value = res.data.customers
		}
	} catch {
		message.error("Failed to load customers")
	} finally {
		loadingCustomers.value = false
	}
}

async function loadCurrentAccess() {
	if (!props.user) return

	try {
		const res = await Api.auth.getUserCustomerAccess(props.user.id)
		if (res.data.success) {
			currentAccess.value = res.data.customer_codes || []
			formModel.value.customerCodes = [...currentAccess.value]
		}
	} catch (error) {
		console.error("Error loading customer access:", error)
		message.error("Failed to load current customer access")
	}
}

function handleAssignCustomers() {
	if (!props.user) return

	loading.value = true

	Api.auth
		.assignCustomerAccess(props.user.id, formModel.value.customerCodes)
		.then(res => {
			if (res.data.success) {
				message.success(res.data.message || "Customer access assigned successfully")
				showModal.value = false
				emit("success")
			} else {
				message.error(res.data.message || "Failed to assign customer access")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Failed to assign customer access")
		})
		.finally(() => {
			loading.value = false
		})
}

watch(showModal, newVal => {
	if (newVal) {
		loadCustomers()
		loadCurrentAccess()
	}
})

// This instance is reused across table rows, so the bound user can change while
// mounted. Reload that user's access if it changes while the modal is open, and
// clear stale state otherwise so a previous user's data is never shown. See #899.
watch(
	() => props.user?.id,
	() => {
		if (showModal.value) {
			loadCurrentAccess()
		} else {
			currentAccess.value = []
			formModel.value.customerCodes = []
		}
	}
)
</script>
