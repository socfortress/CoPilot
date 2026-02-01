<template>
	<div class="customer-provision">
		<transition name="form-fade" mode="out-in">
			<div v-if="editing">
				<CustomerProvisionWizard
					:customer-name="customerNameSanitized"
					:customer-code="customerCode"
					@submitted="submitted"
				>
					<template #additionalActions>
						<n-button @click="editing = false">Close</n-button>
					</template>
				</CustomerProvisionWizard>
			</div>
			<div v-else>
				<div v-if="customerMeta" class="flex items-center justify-end gap-4 px-7 pt-2">
					<n-button size="small" type="error" ghost :loading="loadingDelete" @click="handleDelete">
						<template #icon>
							<Icon :name="DeleteIcon" :size="15" />
						</template>
						Decommission
					</n-button>
				</div>
				<div v-else class="flex items-center justify-between gap-4 px-7 pt-2">
					<n-button size="small" type="primary" @click="editing = true">
						<template #icon>
							<Icon :name="AddIcon" :size="14" />
						</template>
						Create Provision
					</n-button>
				</div>

				<div class="grid-auto-fit-200 grid gap-2 p-7 pt-4">
					<CardKV v-for="(value, key) of customerMeta" :key="key">
						<template #key>
							{{ key }}
						</template>
						<template #value>
							{{ formatValue(key, value) }}
						</template>
					</CardKV>
				</div>
			</div>
		</transition>
	</div>
</template>

<script setup lang="ts">
import type { CustomerMeta } from "@/types/customers.d"
import { NButton, useDialog, useMessage } from "naive-ui"
import { computed, h, ref, toRefs } from "vue"
import Api from "@/api"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import CustomerProvisionWizard from "./CustomerProvisionWizard.vue"

const props = defineProps<{
	customerMeta?: CustomerMeta | null
	customerName?: string | null
	customerCode: string
}>()

const emit = defineEmits<{
	(e: "delete"): void
	(e: "submitted", value: CustomerMeta): void
}>()

const { customerMeta, customerCode, customerName } = toRefs(props)

const DeleteIcon = "ph:trash"
const AddIcon = "carbon:add-alt"

const loadingDelete = ref(false)
const editing = ref(false)
const dialog = useDialog()
const message = useMessage()

const customerNameSanitized = computed<string>(() => customerName.value || customerMeta.value?.customer_name || "")

function formatValue(key: string, value: any): string {
	if (!value) return "-"

	// Add field-specific formatting rules here
	const formatRules: Record<string, (val: any) => string> = {
		customer_meta_index_retention: (val) => `${val} days`
		// Add more formatting rules as needed:
		// another_field: (val) => `${val} units`,
	}

	return formatRules[key] ? formatRules[key](value) : value
}

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
