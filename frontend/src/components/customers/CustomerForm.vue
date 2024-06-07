<template>
	<n-spin :show="loading" class="customer-form">
		<n-form :label-width="80" :model="form" :rules="rules" ref="formRef">
			<div class="flex flex-col gap-4">
				<div class="flex flex-wrap gap-4">
					<div v-for="(_, key) of form" :key="key" class="grow">
						<n-form-item :label="fieldsMeta[key].label" :path="key" class="grow">
							<n-input
								v-model:value.trim="form[key]"
								:placeholder="fieldsMeta[key].placeholder"
								clearable
								:readonly="key === 'customer_code' && lockCode"
								:disabled="key === 'customer_code' && lockCode"
							/>
						</n-form-item>
					</div>
				</div>
				<div class="flex justify-between gap-4">
					<div class="flex gap-4">
						<slot name="additionalActions"></slot>
					</div>
					<div class="flex gap-4">
						<n-button @click="reset()" :disabled="loading">Reset</n-button>
						<n-button type="primary" :disabled="!isValid" @click="validate()" :loading="loading">
							Submit
						</n-button>
					</div>
				</div>
			</div>
		</n-form>
	</n-spin>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, onMounted, ref, toRefs, watch } from "vue"
import Api from "@/api"
import {
	useMessage,
	NForm,
	NFormItem,
	NInput,
	NButton,
	NSpin,
	type FormValidationError,
	type FormInst,
	type FormRules
} from "naive-ui"
import type { Customer } from "@/types/customers.d"
import _trim from "lodash/trim"
import _get from "lodash/get"

const emit = defineEmits<{
	(e: "update:loading", value: boolean): void
	(e: "submitted", value: Customer): void
	(
		e: "mounted",
		value: {
			reset: () => void
		}
	): void
}>()

const props = defineProps<{
	customer?: Customer
	resetOnSubmit?: boolean
	/** lock customer_code on reset and editing (readonly) */
	lockCode?: boolean
}>()
const { customer, resetOnSubmit, lockCode } = toRefs(props)

const loading = ref(false)
const message = useMessage()
const form = ref<Customer>(getClearForm())
const formRef = ref<FormInst | null>(null)

const rules: FormRules = {
	customer_code: {
		required: true,
		message: "Please input code. Code must be all lowercase and contain no spaces or special characters.",
		trigger: ["input", "blur"],
		validator: (rule, value) => {
			if (value !== value.toLowerCase()) {
				return Promise.reject("Code must be all lowercase")
			} else if (!/^[a-z]+$/.test(value)) {
				return Promise.reject("Code must not contain spaces or special characters")
			} else {
				return Promise.resolve()
			}
		}
	},
	customer_name: {
		required: true,
		message: "Please input name",
		trigger: ["input", "blur"]
	},
	contact_last_name: {
		required: true,
		message: "Please input last name",
		trigger: ["input", "blur"]
	},
	contact_first_name: {
		required: true,
		message: "Please input first name",
		trigger: ["input", "blur"]
	}
}

const fieldsMeta = {
	customer_code: {
		label: "Code",
		placeholder: "Unique code for the customer"
	},
	customer_name: {
		label: "Name",
		placeholder: "Name of the customer"
	},
	contact_last_name: {
		label: "Last name",
		placeholder: "Last name of the contact"
	},
	contact_first_name: {
		label: "First name",
		placeholder: "First name of the contact"
	},
	parent_customer_code: {
		label: "Parent Customer Code",
		placeholder: "Code for the parent customer"
	},
	phone: {
		label: "Phone number",
		placeholder: "Phone number"
	},
	address_line1: {
		label: "First line address",
		placeholder: "First line of the address"
	},
	address_line2: {
		label: "Second line address",
		placeholder: "Second line of the address"
	},
	city: {
		label: "City",
		placeholder: "City"
	},
	state: {
		label: "State",
		placeholder: "State"
	},
	postal_code: {
		label: "Postal Code",
		placeholder: "Postal Code"
	},
	country: {
		label: "Country",
		placeholder: "Country"
	},
	customer_type: {
		label: "Type",
		placeholder: "Type of the customer"
	},
	logo_file: {
		label: "Logo",
		placeholder: "Logo file for the customer"
	}
}

const isValid = computed(() => {
	let valid = true

	for (const key in rules) {
		const rule = rules[key] as FormRules

		if (rule.required && !_trim(_get(form.value, key))) {
			valid = false
		}
	}

	return valid
})

function validate() {
	if (!formRef.value) return

	formRef.value.validate((errors?: Array<FormValidationError>) => {
		if (!errors) {
			submit()
		} else {
			message.warning("You must fill in the required fields correctly.")
			return false
		}
	})
}

function getClearForm(customer?: Partial<Customer>) {
	return {
		customer_code: customer?.customer_code || "",
		customer_name: customer?.customer_name || "",
		contact_last_name: customer?.contact_last_name || "",
		contact_first_name: customer?.contact_first_name || "",
		parent_customer_code: customer?.parent_customer_code || "",
		phone: customer?.phone || "",
		address_line1: customer?.address_line1 || "",
		address_line2: customer?.address_line2 || "",
		city: customer?.city || "",
		state: customer?.state || "",
		postal_code: customer?.postal_code || "",
		country: customer?.country || "",
		customer_type: customer?.customer_type || "",
		logo_file: customer?.logo_file || ""
	}
}

function reset() {
	let fields = undefined
	if (lockCode.value) {
		fields = { customer_code: customer.value?.customer_code || "" }
	}
	form.value = getClearForm(fields)
}

function submit() {
	loading.value = true

	const method = customer.value?.customer_code ? "updateCustomer" : "createCustomer"

	Api.customers[method](form.value, customer.value?.customer_code)
		.then(res => {
			if (res.data.success) {
				emit("submitted", res.data.customer)
				if (resetOnSubmit.value) {
					reset()
				}
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

function setForm() {
	form.value = getClearForm(customer.value)
}

watch(loading, val => {
	emit("update:loading", val)
})

watch(customer, val => {
	if (val) {
		setForm()
	}
})

onBeforeMount(() => {
	if (customer.value) {
		setForm()
	}
})

onMounted(() => {
	emit("mounted", {
		reset
	})
})
</script>
