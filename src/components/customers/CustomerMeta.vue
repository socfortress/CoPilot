<template>
	<div class="customer-meta">
		<div class="p-7 pt-4" v-if="editing">
			<CustomerMetaForm
				@submitted="submitted"
				:customerMeta="customerMeta || undefined"
				:customerCode="customerCode"
			>
				<template #additionalActions>
					<n-button @click="editing = false">Close</n-button>
				</template>
			</CustomerMetaForm>
		</div>
		<template v-else>
			<div class="flex items-center justify-between gap-4 px-7 pt-2" v-if="customerMeta">
				<n-button size="small" @click="editing = true" :disabled="loadingDelete">
					<template #icon>
						<Icon :name="EditIcon" :size="14"></Icon>
					</template>
					Edit
				</n-button>
				<n-button size="small" type="error" ghost @click="handleDelete" :loading="loadingDelete">
					<template #icon>
						<Icon :name="DeleteIcon" :size="15"></Icon>
					</template>
					Clear Meta
				</n-button>
			</div>
			<div class="flex items-center justify-between gap-4 px-7 pt-2" v-else>
				<n-button size="small" @click="editing = true" type="primary">
					<template #icon>
						<Icon :name="AddIcon" :size="14"></Icon>
					</template>
					Add Meta
				</n-button>
			</div>

			<div class="grid gap-2 grid-auto-flow-200 p-7 pt-4">
				<KVCard v-for="(value, key) of customerMeta" :key="key">
					<template #key>{{ key }}</template>
					<template #value>{{ value || "-" }}</template>
				</KVCard>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import { h, ref, toRefs } from "vue"
import KVCard from "@/components/common/KVCard.vue"
import CustomerMetaForm from "./CustomerMetaForm.vue"
import Api from "@/api"
import { useMessage, NButton, useDialog } from "naive-ui"
import type { CustomerMeta } from "@/types/customers.d"

const emit = defineEmits<{
	(e: "delete"): void
	(e: "submitted", value: CustomerMeta): void
}>()

const props = defineProps<{
	customerMeta?: CustomerMeta | null
	customerCode: string
}>()
const { customerMeta, customerCode } = toRefs(props)

const EditIcon = "uil:edit-alt"
const DeleteIcon = "ph:trash"
const AddIcon = "carbon:add-alt"

const loadingDelete = ref(false)
const editing = ref(false)
const dialog = useDialog()
const message = useMessage()

function submitted(newData: CustomerMeta) {
	emit("submitted", newData)
	editing.value = false
}

function deleteCustomer() {
	loadingDelete.value = true

	Api.customers
		.deleteCustomerMeta(customerCode.value)
		.then(res => {
			if (res.data.success) {
				emit("delete")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingDelete.value = false
		})
}

function handleDelete() {
	dialog.warning({
		title: "Confirm",
		content: () =>
			h("div", {
				innerHTML: `Are you sure you want to delete Meta tags for the Customer: <strong>${customerCode.value}</strong> ?`
			}),
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deleteCustomer()
		},
		onNegativeClick: () => {
			message.info("Delete canceled")
		}
	})
}
</script>
