<template>
	<n-spin :show="loading" class="customer-form">
		<n-form :label-width="80" :model="form" :rules="rules" ref="formRef">
			<div class="flex flex-col gap-4">
				<div class="flex flex-wrap gap-4">
					<div v-for="(val, key) of form" :key="key" class="grow">
						<n-form-item :label="key" :path="key" class="grow">
							<n-input v-model:value.trim="form[key]" :placeholder="key" clearable />
						</n-form-item>
					</div>
				</div>
				<div class="flex justify-end gap-4">
					<n-button>Reset</n-button>
					<n-button type="primary" :disabled="!isValid">Submit</n-button>
				</div>
			</div>
		</n-form>
	</n-spin>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, ref, toRefs } from "vue"
import Api from "@/api"
import {
	NImage,
	NAvatar,
	useMessage,
	NForm,
	NFormItem,
	NInput,
	NButton,
	NCollapseItem,
	NPopover,
	NModal,
	NTabs,
	NTabPane,
	NSpin,
	NTooltip,
	type FormItemRule,
	type FormValidationError,
	type FormInst,
	type FormRules
} from "naive-ui"
import type { Customer } from "@/types/customers.d"
import Icon from "@/components/common/Icon.vue"
import dayjs from "@/utils/dayjs"
import _trim from "lodash/trim"
import _get from "lodash/get"

const emit = defineEmits<{
	(e: "added"): void
}>()

/*
const props = defineProps<{
	customer: Customer
	highlight?: boolean | null | undefined
}>()
const { customer, highlight } = toRefs(props)
*/

const DetailsIcon = "carbon:settings-adjust"

const loading = ref(false)
const message = useMessage()
const form = ref<Customer>(getClearForm())
const formRef = ref<FormInst | null>(null)

const rules: FormRules = {
	customer_code: {
		required: true,
		message: "Please input customer code",
		trigger: ["input", "blur"]
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
			console.log(errors)
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

onBeforeMount(() => {
	//reset()
})
</script>

<style lang="scss" scoped>
.customer-form {
}
</style>
