<template>
	<div class="customer-info">
		<div v-if="editing" class="p-7 pt-4">
			<CustomerForm :customer="customer" :lock-code="true" @submitted="submitted">
				<template #additionalActions>
					<n-button @click="editing = false">Close</n-button>
				</template>
			</CustomerForm>
		</div>
		<template v-else>
			<div class="flex items-center justify-between gap-4 px-7 pt-2">
				<n-button size="small" :disabled="loadingDelete" @click="editing = true">
					<template #icon>
						<Icon :name="EditIcon" :size="14"></Icon>
					</template>
					Edit
				</n-button>
				<n-button size="small" type="error" ghost :loading="loadingDelete" @click="handleDelete">
					<template #icon>
						<Icon :name="DeleteIcon" :size="15"></Icon>
					</template>
					Delete Customer
				</n-button>
			</div>

			<div class="grid-auto-fit-200 grid gap-2 p-7 pt-4">
				<CardKV v-for="(value, key) of customer" :key="key">
					<template #key>
						{{ key }}
					</template>
					<template #value>
						{{ value || "-" }}
					</template>
				</CardKV>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import type { Customer } from "@/types/customers.d"
import Api from "@/api"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { NButton, useDialog, useMessage } from "naive-ui"
import { h, ref, toRefs, watch } from "vue"
import CustomerForm from "./CustomerForm.vue"

const props = defineProps<{
	customer: Customer
}>()

const emit = defineEmits<{
	(e: "update:loading", value: boolean): void
	(e: "delete"): void
	(e: "submitted", value: Customer): void
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
