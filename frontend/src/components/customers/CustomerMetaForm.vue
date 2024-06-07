<template>
	<n-spin :show="loading" class="customer-meta-form">
		<n-form :label-width="80" :model="form" :rules="rules" ref="formRef">
			<div class="flex flex-col gap-4">
				<div class="flex flex-wrap gap-4">
					<div v-for="(_, key) of form" :key="key" class="grow">
						<n-form-item :label="fieldsMeta[key].label" :path="key" class="grow">
							<n-input
								v-model:value.trim="form[key]"
								:placeholder="fieldsMeta[key].placeholder"
								:readonly="!!fieldsMeta[key].readonly"
								clearable
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
import type { CustomerMeta } from "@/types/customers.d"
import _trim from "lodash/trim"
import _get from "lodash/get"
import _toSafeInteger from "lodash/toSafeInteger"

interface CustomerMetaExt extends Omit<CustomerMeta, "id" | "customer_meta_iris_customer_id"> {
	id: string
	customer_meta_iris_customer_id: string
}

const emit = defineEmits<{
	(e: "update:loading", value: boolean): void
	(e: "submitted", value: CustomerMeta): void
	(
		e: "mounted",
		value: {
			reset: () => void
		}
	): void
}>()

const props = defineProps<{
	customerMeta?: CustomerMeta
	customerCode: string
	customerName: string
	metaId: number
	resetOnSubmit?: boolean
}>()
const { customerMeta, customerCode, customerName, metaId, resetOnSubmit } = toRefs(props)

const loading = ref(false)
const message = useMessage()
const form = ref<CustomerMetaExt>(getClearForm())
const formRef = ref<FormInst | null>(null)

const rules: FormRules = {
	customer_meta_graylog_index: {
		required: true,
		message: "Please input Graylog Index",
		trigger: ["input", "blur"]
	},
	customer_meta_graylog_stream: {
		required: true,
		message: "Please input Graylog Stream",
		trigger: ["input", "blur"]
	},
	customer_meta_grafana_org_id: {
		required: true,
		message: "Please input Grafana Org Id",
		trigger: ["input", "blur"]
	},
	customer_meta_index_retention: {
		required: true,
		message: "Please input Index retention",
		trigger: ["input", "blur"]
	},
	customer_meta_wazuh_group: {
		required: true,
		message: "Please input Wazuh Group",
		trigger: ["input", "blur"]
	},
	customer_meta_wazuh_registration_port: {
		required: true,
		message: "Please input Wazuh registration port",
		trigger: ["input", "blur"]
	},
	customer_meta_wazuh_log_ingestion_port: {
		required: true,
		message: "Please input Wazuh log ingestion port",
		trigger: ["input", "blur"]
	},
	customer_meta_wazuh_auth_password: {
		required: true,
		message: "Please input Wazuh auth password",
		trigger: ["input", "blur"]
	},
	customer_meta_iris_customer_id: {
		required: true,
		message: "Please input Wazuh auth password",
		trigger: ["input", "blur"]
	},
	customer_meta_office365_organization_id: {
		required: true,
		message: "Please input Wazuh auth password",
		trigger: ["input", "blur"]
	}
}

const fieldsMeta: { [key: string]: { label: string; placeholder: string; readonly?: boolean } } = {
	id: {
		label: "Meta ID",
		placeholder: "Meta ID...",
		readonly: true
	},
	customer_code: {
		label: "Customer Code",
		placeholder: "Customer Code...",
		readonly: true
	},
	customer_name: {
		label: "Customer Name",
		placeholder: "Customer Name...",
		readonly: true
	},
	customer_meta_graylog_index: {
		label: "Graylog Index",
		placeholder: "Graylog Index..."
	},
	customer_meta_graylog_stream: {
		label: "Graylog Stream",
		placeholder: "Graylog Stream..."
	},
	customer_meta_grafana_org_id: {
		label: "Grafana Org Id",
		placeholder: "Grafana Org Id..."
	},
	customer_meta_index_retention: {
		label: "Index retention",
		placeholder: "Index retention..."
	},
	customer_meta_wazuh_group: {
		label: "Wazuh Group",
		placeholder: "Wazuh Group..."
	},
	customer_meta_wazuh_registration_port: {
		label: "Wazuh registration port",
		placeholder: "Wazuh registration port..."
	},
	customer_meta_wazuh_log_ingestion_port: {
		label: "Wazuh log ingestion port",
		placeholder: "Wazuh log ingestion port..."
	},
	customer_meta_wazuh_auth_password: {
		label: "Wazuh auth password",
		placeholder: "Wazuh auth password..."
	},
	customer_meta_iris_customer_id: {
		label: "Iris Customer ID",
		placeholder: "Iris Customer ID..."
	},
	customer_meta_office365_organization_id: {
		label: "Office365 Organization ID",
		placeholder: "Office365 Organization ID..."
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

function getClearForm(customerMeta?: Partial<CustomerMeta>): CustomerMetaExt {
	return {
		id: metaId.value?.toString() || "",
		customer_code: customerCode.value || "",
		customer_name: customerName.value || "",
		customer_meta_graylog_index: customerMeta?.customer_meta_graylog_index || "",
		customer_meta_graylog_stream: customerMeta?.customer_meta_graylog_stream || "",
		customer_meta_grafana_org_id: customerMeta?.customer_meta_grafana_org_id || "",
		customer_meta_index_retention: customerMeta?.customer_meta_index_retention || "",
		customer_meta_wazuh_group: customerMeta?.customer_meta_wazuh_group || "",
		customer_meta_wazuh_registration_port: customerMeta?.customer_meta_wazuh_registration_port || "",
		customer_meta_wazuh_log_ingestion_port: customerMeta?.customer_meta_wazuh_log_ingestion_port || "",
		customer_meta_wazuh_auth_password: customerMeta?.customer_meta_wazuh_auth_password || "",
		customer_meta_iris_customer_id: customerMeta?.customer_meta_iris_customer_id?.toString() || "",
		customer_meta_office365_organization_id: customerMeta?.customer_meta_office365_organization_id || ""
	}
}

function getPayload(meta: CustomerMetaExt): CustomerMeta {
	return {
		id: _toSafeInteger(meta.id),
		customer_code: meta.customer_code,
		customer_name: meta.customer_name,
		customer_meta_graylog_index: meta.customer_meta_graylog_index,
		customer_meta_graylog_stream: meta.customer_meta_graylog_stream,
		customer_meta_grafana_org_id: meta.customer_meta_grafana_org_id,
		customer_meta_wazuh_group: meta.customer_meta_wazuh_group,
		customer_meta_index_retention: meta.customer_meta_index_retention,
		customer_meta_wazuh_registration_port: meta.customer_meta_wazuh_registration_port,
		customer_meta_wazuh_log_ingestion_port: meta.customer_meta_wazuh_log_ingestion_port,
		customer_meta_wazuh_auth_password: meta.customer_meta_wazuh_auth_password,
		customer_meta_iris_customer_id: _toSafeInteger(meta.customer_meta_iris_customer_id),
		customer_meta_office365_organization_id: meta.customer_meta_office365_organization_id
	}
}

function reset() {
	if (!loading.value) {
		resetForm()
		formRef.value?.restoreValidation()
	}
}

function resetForm() {
	form.value = getClearForm()
}

function submit() {
	loading.value = true

	const method = customerMeta.value?.customer_meta_graylog_index ? "updateCustomerMeta" : "createCustomerMeta"

	Api.customers[method](getPayload(form.value), customerCode.value)
		.then(res => {
			if (res.data.success) {
				emit("submitted", res.data.customer_meta)
				if (resetOnSubmit.value) {
					resetForm()
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
	form.value = getClearForm(customerMeta.value)
}

watch(loading, val => {
	emit("update:loading", val)
})

watch(customerMeta, val => {
	if (val) {
		setForm()
	}
})

onBeforeMount(() => {
	if (customerMeta.value) {
		setForm()
	}
})

onMounted(() => {
	emit("mounted", {
		reset
	})
})
</script>
