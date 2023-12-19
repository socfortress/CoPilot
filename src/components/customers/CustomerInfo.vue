<template>
	<div class="customer-info">
		<div class="p-7 pt-4" v-if="editing">
			<CustomerForm @submitted="submitted" :customer="customer" :lockCode="true">
				<template #additionalActions>
					<n-button @click="editing = false">Close</n-button>
				</template>
			</CustomerForm>
		</div>
		<template v-else>
			<div class="flex items-center justify-between gap-4 px-7 pt-2">
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
					Delete Customer
				</n-button>
			</div>

			<div class="grid gap-2 grid-auto-flow-200 p-7 pt-4">
				<KVCard v-for="(value, key) of customer" :key="key">
					<template #key>{{ key }}</template>
					<template #value>{{ value || "-" }}</template>
				</KVCard>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import { h, ref, toRefs, watch } from "vue"
import KVCard from "@/components/common/KVCard.vue"
import CustomerForm from "./CustomerForm.vue"
import Api from "@/api"
import { useMessage, NButton, useDialog } from "naive-ui"
import type { Customer } from "@/types/customers.d"

const emit = defineEmits<{
	(e: "update:loading", value: boolean): void
	(e: "delete"): void
	(e: "submitted", value: Customer): void
}>()

const props = defineProps<{
	customer: Customer
}>()
const { customer } = toRefs(props)

const EditIcon = "uil:edit-alt"
const DeleteIcon = "ph:trash"

const loadingDelete = ref(false)
const editing = ref(false)
const dialog = useDialog()
const message = useMessage()

function submitted(newData: Customer) {
	emit("submitted", newData)
	editing.value = false
}

function deleteCustomer() {
	loadingDelete.value = true

	Api.customers
		.deleteCustomer(customer.value.customer_code)
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
				innerHTML: `Are you sure you want to delete the Customer: <strong>${customer.value.customer_code}</strong> ?`
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

watch(loadingDelete, val => {
	emit("update:loading", val)
})
</script>
