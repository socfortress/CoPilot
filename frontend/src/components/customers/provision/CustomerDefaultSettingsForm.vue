<template>
	<n-spin :show="loading" class="customer-provisioning-default-settings-form">
		<n-form :label-width="80" :model="form" :rules="rules" ref="formRef">
			<div class="flex flex-col gap-4">
				<div class="flex flex-wrap gap-4">
					<div v-for="(_, key) of form" :key="key" class="grow">
						<n-form-item :label="fieldsMeta[key].label" :path="key" class="grow">
							<n-input
								v-model:value.trim="form[key]"
								:placeholder="fieldsMeta[key].placeholder"
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
						<n-button
							type="primary"
							:disabled="!isValid"
							@click="validate()"
							:loading="submittingDefaultSettings"
						>
							Submit
						</n-button>
					</div>
				</div>
			</div>
		</n-form>
	</n-spin>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, onMounted, ref, watch } from "vue"
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
	type FormRules,
	type FormItemRule
} from "naive-ui"
import type { CustomerProvisioningDefaultSettings } from "@/types/customers.d"
import _trim from "lodash/trim"
import _get from "lodash/get"
import isURL from "validator/es/lib/isURL"
import isIP from "validator/es/lib/isIP"

const emit = defineEmits<{
	(e: "update:loading", value: boolean): void
	(
		e: "mounted",
		value: {
			load: () => void
		}
	): void
}>()

const loadingDefaultSettings = ref(false)
const submittingDefaultSettings = ref(false)
const loading = computed(() => loadingDefaultSettings.value || submittingDefaultSettings.value)
const message = useMessage()
const form = ref<Omit<CustomerProvisioningDefaultSettings, "id">>(getClearForm())
const formRef = ref<FormInst | null>(null)
const entityId = ref(0)

const rules: FormRules = {
	cluster_name: {
		message: "Please input the Cluster Name",
		trigger: ["input", "blur"]
	},
	cluster_key: {
		message: "Please input the Cluster Key",
		trigger: ["input", "blur"]
	},
	master_ip: {
		validator: validateIp,
		trigger: ["blur"]
	},
	grafana_url: {
		validator: validateUrl,
		trigger: ["blur"]
	},
	wazuh_worker_hostname: {
		message: "Please input the Wazuh Worker Hostname",
		trigger: ["input", "blur"]
	}
}

const fieldsMeta = {
	cluster_name: {
		label: "Cluster Name",
		placeholder: "Insert the Cluster Name"
	},
	cluster_key: {
		label: "Cluster Key",
		placeholder: "Insert the Cluster Key"
	},
	master_ip: {
		label: "Master IP",
		placeholder: "Insert the Master IP"
	},
	grafana_url: {
		label: "Grafana URL",
		placeholder: "Insert the Grafana URL"
	},
	wazuh_worker_hostname: {
		label: "Wazuh Worker Hostname",
		placeholder: "Insert the Wazuh Worker Hostname"
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

function getClearForm(settings?: Partial<CustomerProvisioningDefaultSettings>) {
	const payload = {
		cluster_name: settings?.cluster_name || "",
		cluster_key: settings?.cluster_key || "",
		master_ip: settings?.master_ip || "",
		grafana_url: settings?.grafana_url || "",
		wazuh_worker_hostname: settings?.wazuh_worker_hostname || ""
	}
	return payload
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
	submittingDefaultSettings.value = true

	const method = entityId.value ? "updateProvisioningDefaultSettings" : "setProvisioningDefaultSettings"

	const payload = {
		id: entityId.value || 0,
		clusterName: form.value.cluster_name,
		clusterKey: form.value.cluster_key,
		masterIp: form.value.master_ip,
		grafanaUrl: form.value.grafana_url,
		wazuhWorkerHostname: form.value.wazuh_worker_hostname
	}

	Api.customers[method](payload)
		.then(res => {
			if (res.data.success) {
				entityId.value = res.data.customer_provisioning_default_settings.id
				message.success(res.data?.message || "Customer Provisioning Default Settings updated successfully")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			submittingDefaultSettings.value = false
		})
}

function setForm(settings?: CustomerProvisioningDefaultSettings) {
	form.value = getClearForm(settings)
}

function validateIp(rule: FormItemRule, value: string) {
	if (value && !isIP(value)) {
		return new Error("Please input a valid IP Address")
	}

	return true
}

function validateUrl(rule: FormItemRule, value: string) {
	if (value && !isURL(value, { require_tld: false })) {
		return new Error("Please input a valid URL")
	}

	return true
}

function getProvisioningDefaultSettings() {
	loadingDefaultSettings.value = true

	Api.customers
		.getProvisioningDefaultSettings()
		.then(res => {
			if (res.data.success) {
				entityId.value = res.data.customer_provisioning_default_settings.id || 0
				setForm(res.data?.customer_provisioning_default_settings)
			}
		})
		.finally(() => {
			loadingDefaultSettings.value = false
		})
}

function load() {
	if (!loadingDefaultSettings.value) {
		getProvisioningDefaultSettings()
	}
}

watch(loading, val => {
	emit("update:loading", val)
})

onBeforeMount(() => {
	getProvisioningDefaultSettings()
})

onMounted(() => {
	emit("mounted", {
		load
	})
})
</script>
