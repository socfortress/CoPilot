<template>
	<n-spin :show="loading" class="customer-form">
		<n-form :label-width="80" :model="form" :rules="rules" ref="formRef">
			<div class="flex flex-col gap-4">
				<div class="flex flex-wrap gap-4">
					<div v-for="(val, key) of form" :key="key" class="grow">
						<n-form-item :label="fieldsMeta[key].label" :path="key" class="grow">
							<n-input
								v-model:value.trim="form[key]"
								:placeholder="fieldsMeta[key].placeholder"
								clearable
							/>
						</n-form-item>
					</div>
				</div>
				<div class="flex justify-end gap-4">
					<n-button @click="reset()">Reset</n-button>
					<n-button type="primary" :disabled="!isValid" @click="validate()">Submit</n-button>
				</div>
			</div>
		</n-form>
	</n-spin>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, onMounted, ref } from "vue"
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
	(e: "added", value: Customer): void
	(
		e: "mounted",
		value: {
			reset: () => void
		}
	): void
}>()

/*
const props = defineProps<{
	customer: Customer
	highlight?: boolean | null | undefined
}>()
const { customer, highlight } = toRefs(props)
*/

const loading = ref(false)
const message = useMessage()
const form = ref<Customer>(getClearForm())
const formRef = ref<FormInst | null>(null)

const rules: FormRules = {
	customer_code: {
		required: true,
		message: "Please input code",
		trigger: ["input", "blur"]
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

function getClearForm() {
	return {
		customer_code: "",
		customer_name: "",
		contact_last_name: "",
		contact_first_name: "",
		parent_customer_code: "",
		phone: "",
		address_line1: "",
		address_line2: "",
		city: "",
		state: "",
		postal_code: "",
		country: "",
		customer_type: "",
		logo_file: ""
	}
}

function reset() {
	form.value = getClearForm()
}

function submit() {
	loading.value = true

	Api.customers
		.createCustomer(form.value)
		.then(res => {
			if (res.data.success) {
				reset()
				emit("added", res.data.customer)
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

onMounted(() => {
	emit("mounted", {
		reset
	})
})
</script>

<style lang="scss" scoped>
.customer-form {
}
</style>
