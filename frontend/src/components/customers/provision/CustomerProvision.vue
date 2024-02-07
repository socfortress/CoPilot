<template>
	<div class="customer-provision">
		<transition name="form-fade" mode="out-in">
			<div v-if="editing">
				<CustomerProvisionWizard
					@submitted="submitted"
					:customerName="customerNameSanitized"
					:customerCode="customerCode"
				>
					<template #additionalActions>
						<n-button @click="editing = false">Close</n-button>
					</template>
				</CustomerProvisionWizard>
			</div>
			<div v-else>
				<div class="flex items-center justify-end gap-4 px-7 pt-2" v-if="customerMeta">
					<n-button size="small" type="error" ghost @click="handleDelete" :loading="loadingDelete">
						<template #icon>
							<Icon :name="DeleteIcon" :size="15"></Icon>
						</template>
						Decommission
					</n-button>
				</div>
				<div class="flex items-center justify-between gap-4 px-7 pt-2" v-else>
					<n-button size="small" @click="editing = true" type="primary">
						<template #icon>
							<Icon :name="AddIcon" :size="14"></Icon>
						</template>
						Create Provision
					</n-button>
				</div>

				<div class="grid gap-2 grid-auto-flow-200 p-7 pt-4">
					<KVCard v-for="(value, key) of customerMeta" :key="key">
						<template #key>{{ key }}</template>
						<template #value>{{ value || "-" }}</template>
					</KVCard>
				</div>
			</div>
		</transition>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import { computed, h, ref, toRefs } from "vue"
import KVCard from "@/components/common/KVCard.vue"
import CustomerProvisionWizard from "./CustomerProvisionWizard.vue"
import Api from "@/api"
import { useMessage, NButton, useDialog } from "naive-ui"
import type { CustomerMeta } from "@/types/customers.d"

const emit = defineEmits<{
	(e: "delete"): void
	(e: "submitted", value: CustomerMeta): void
}>()

const props = defineProps<{
	customerMeta?: CustomerMeta | null
	customerName?: string | null
	customerCode: string
}>()
const { customerMeta, customerCode, customerName } = toRefs(props)

const DeleteIcon = "ph:trash"
const AddIcon = "carbon:add-alt"

const loadingDelete = ref(false)
const editing = ref(false)
const dialog = useDialog()
const message = useMessage()

const customerNameSanitized = computed<string>(() => customerName.value || customerMeta.value?.customer_name || "")

function submitted(newData: CustomerMeta) {
	emit("submitted", newData)
	editing.value = false
}

function decommissionCustomer() {
	loadingDelete.value = true

	Api.customers
		.decommissionCustomer(customerCode.value)
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
				innerHTML: `Are you sure you want to dismiss Customer: <strong>${customerCode.value}</strong> ?`
			}),
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			decommissionCustomer()
		},
		onNegativeClick: () => {
			message.info("Decommission canceled")
		}
	})
}
</script>

<style lang="scss" scoped>
.customer-provision {
	.form-fade-enter-active,
	.form-fade-leave-active {
		transition:
			opacity 0.2s ease-in-out,
			transform 0.3s ease-in-out;
	}
	.form-fade-enter-from {
		opacity: 0;
		transform: translateY(10px);
	}
	.form-fade-leave-to {
		opacity: 0;
		transform: translateY(-10px);
	}
}
</style>
