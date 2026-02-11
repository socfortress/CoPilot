<template>
	<n-spin :show="loading" class="customer-provision-wizard">
		<div class="flex min-h-120 flex-col">
			<div class="grow">
				<n-scrollbar x-scrollable trigger="none">
					<div class="p-7 pt-4">
						<n-steps :current size="small" :status="currentStatus">
							<n-step title="Provisioning" />
							<n-step title="Graylog" />
							<n-step title="Subscription" />
							<n-step title="Infrastructure">
								<template #icon>
									<Icon v-if="!isInfrastructureEnabled" :name="SkipIcon" />
								</template>
							</n-step>
							<n-step title="Wazuh Worker" :status="!isWazuhStepEnabled ? 'wait' : undefined">
								<template #icon>
									<Icon v-if="!isWazuhStepEnabled" :name="SkipIcon" />
								</template>
							</n-step>
						</n-steps>
					</div>
				</n-scrollbar>

				<n-form ref="formRef" :label-width="80" :model="form" :rules="rules" class="form-container mt-4">
					<Transition :name="`slide-form-${slideFormDirection}`">
						<div v-if="current === 1" class="flex flex-col gap-3 px-7">
							<div class="flex flex-wrap gap-3">
								<n-form-item label="Customer Code" path="customer_code" class="grow">
									<n-input
										v-model:value.trim="form.customer_code"
										placeholder="Input Customer Code..."
										readonly
										disabled
									/>
								</n-form-item>
								<n-form-item label="Customer Name" path="customer_name" class="grow">
									<n-input
										v-model:value.trim="form.customer_name"
										placeholder="Input Customer Name..."
										readonly
										disabled
									/>
								</n-form-item>
							</div>
							<n-form-item
								label="Customer Grafana.org Name"
								path="customer_grafana_org_name"
								class="grow"
							>
								<n-input
									v-model:value.trim="form.customer_grafana_org_name"
									placeholder="Customer Grafana.org Name..."
									clearable
								/>
							</n-form-item>
							<n-form-item
								v-if="showDfirIrisUsername"
								label="DFIR-IRIS Username"
								path="dfir_iris_username"
								class="grow"
							>
								<n-input
									v-model:value.trim="form.dfir_iris_username"
									placeholder="The Username of the API Key CoPilot uses to connect to DFIR-IRIS..."
									clearable
								/>
							</n-form-item>
						</div>

						<div v-else-if="current === 2" class="flex flex-col gap-3 px-7">
							<div class="flex flex-col gap-3 sm:flex-row">
								<n-form-item
									label="Customer Index name"
									path="customer_index_name"
									class="grow basis-1/2"
								>
									<n-input
										v-model:value.trim="form.customer_index_name"
										placeholder="Customer Index name..."
										clearable
										class="grow"
									/>
								</n-form-item>

								<n-form-item label="Index replicas" path="index_replicas" class="grow basis-1/2">
									<n-input-number v-model:value="form.index_replicas" min="0" class="grow" />
								</n-form-item>
							</div>
							<div class="flex flex-wrap gap-3">
								<n-form-item label="Index shards" path="index_shards" class="grow">
									<n-input-number v-model:value="form.index_shards" min="0" class="grow" />
								</n-form-item>
								<n-form-item label="Hot Data Retention (days)" path="hot_data_retention" class="grow">
									<n-input-number v-model:value="form.hot_data_retention" min="0" class="grow" />
								</n-form-item>
							</div>
						</div>

						<div v-else-if="current === 3" class="flex flex-col gap-3 px-7">
							<n-form-item label="Subscriptions" path="customer_subscription" class="grow">
								<n-select
									v-model:value="form.customer_subscription"
									:options="subscriptionOptions"
									:loading="loadingSubscriptions"
									:placeholder="
										loadingSubscriptions ? 'Loading Subscriptions...' : 'Select Subscriptions'
									"
									multiple
									clearable
									to="body"
									class="grow"
								/>
							</n-form-item>
							<n-form-item
								path="dashboards_to_include.dashboards"
								class="grow"
								label-style="flex-direction: column; align-items: stretch;"
								:show-require-mark="false"
							>
								<template #label>
									<div class="flex w-full items-center justify-between gap-4">
										<div>
											Dashboards
											<span class="n-form-item-label__asterisk">*</span>
										</div>
										<div>
											<n-button
												v-if="dashboardOptions.length"
												size="tiny"
												@click="toggleDashboards()"
											>
												{{ allDashboardsSelected ? "Deselect All" : "Select All" }}
											</n-button>
										</div>
									</div>
								</template>
								<n-select
									v-model:value="form.dashboards_to_include.dashboards"
									:options="dashboardOptions"
									:loading="loadingDashboards"
									:placeholder="loadingDashboards ? 'Loading Dashboards...' : 'Select Dashboards'"
									multiple
									clearable
									to="body"
									class="grow"
								/>
							</n-form-item>
						</div>

						<div v-else-if="current === 4" class="flex gap-3 px-7">
							<n-card class="grow">
								<n-form-item label="Deploy Wazuh Worker" path="provision_wazuh_worker">
									<n-switch v-model:value="form.provision_wazuh_worker" clearable />
								</n-form-item>
								<div class="text-secondary mt-2 text-sm">
									Multi-tenancy (SOCFortress Pro Services only): Deploys a dedicated worker used in
									SOCFortress-managed multi-tenant Wazuh environments. Leave off for single-tenant
									deployments.
								</div>
							</n-card>
							<n-card class="grow">
								<n-form-item label="Deploy HA Proxy" path="provision_ha_proxy">
									<n-switch
										v-model:value="form.provision_ha_proxy"
										clearable
										:disabled="!form.provision_wazuh_worker"
									/>
								</n-form-item>
								<div class="text-secondary mt-2 text-sm">
									Multi-tenancy (SOCFortress Pro Services only): Deploys the load balancer used to
									route agent connections across multi-tenant Wazuh workers for high availability.
									Leave off for single-tenant deployments.
								</div>
							</n-card>
						</div>

						<div v-else-if="current === 5" class="flex flex-col gap-3 px-7">
							<div class="flex flex-wrap gap-3">
								<n-form-item label="Auth Password" path="wazuh_auth_password" class="grow">
									<n-input
										v-model:value="form.wazuh_auth_password"
										placeholder="Auth Password..."
										clearable
									/>
								</n-form-item>
								<n-form-item label="Registration Port" path="wazuh_registration_port" class="grow">
									<n-input
										v-model:value="form.wazuh_registration_port"
										placeholder="Registration Port..."
										clearable
										@blur="validate()"
									/>
								</n-form-item>
								<n-form-item label="Logs Port" path="wazuh_logs_port" class="grow">
									<n-input
										v-model:value="form.wazuh_logs_port"
										placeholder="Logs Port..."
										clearable
										@blur="validate()"
									/>
								</n-form-item>
								<n-form-item label="Api Port" path="wazuh_api_port" class="grow">
									<n-input
										v-model:value="form.wazuh_api_port"
										placeholder="Api Port..."
										clearable
										@blur="validate()"
									/>
								</n-form-item>
								<n-form-item label="Cluster Name" path="wazuh_cluster_name" class="grow">
									<n-input
										v-model:value="form.wazuh_cluster_name"
										placeholder="Cluster Name..."
										clearable
									/>
								</n-form-item>
								<n-form-item label="Cluster Key" path="wazuh_cluster_key" class="grow">
									<n-input
										v-model:value="form.wazuh_cluster_key"
										placeholder="Cluster Key..."
										clearable
									/>
								</n-form-item>
								<n-form-item label="Master IP" path="wazuh_master_ip" class="grow">
									<n-input
										v-model:value="form.wazuh_master_ip"
										placeholder="Master IP..."
										clearable
									/>
								</n-form-item>
								<n-form-item label="Grafana Url" path="grafana_url" class="grow">
									<n-input v-model:value="form.grafana_url" placeholder="Grafana Url..." clearable />
								</n-form-item>
							</div>
							<n-form-item
								v-if="form.provision_ha_proxy"
								label="Worker Hostname"
								path="wazuh_worker_hostname"
								class="grow"
							>
								<n-input
									v-model:value="form.wazuh_worker_hostname"
									placeholder="Worker Hostname..."
									clearable
								/>
							</n-form-item>
							<div>* Registration Port, Logs Port, and Api Port must all be unique.</div>
						</div>
					</Transition>
				</n-form>
			</div>

			<div class="flex justify-between gap-4 p-7 pt-4">
				<div class="flex gap-4">
					<slot name="additionalActions"></slot>
				</div>
				<div class="flex gap-4">
					<n-button v-if="isPrevStepEnabled" @click="prev()">
						<template #icon>
							<Icon :name="ArrowLeftIcon" />
						</template>
						Prev
					</n-button>
					<n-button v-if="isNextStepEnabled" icon-placement="right" @click="next()">
						<template #icon>
							<Icon :name="ArrowRightIcon" />
						</template>
						Next
					</n-button>
					<n-button v-if="isSubmitEnabled" type="primary" :loading="loading" @click="validate(submit)">
						Submit
					</n-button>
				</div>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { FormInst, FormItemRule, FormRules, FormValidationError, StepsProps } from "naive-ui"
import type { CustomerMeta, CustomerProvision, CustomerProvisioningDefaultSettings } from "@/types/customers.d"
import _uniqBy from "lodash/uniqBy"
import {
	NButton,
	NCard,
	NForm,
	NFormItem,
	NInput,
	NInputNumber,
	NScrollbar,
	NSelect,
	NSpin,
	NStep,
	NSteps,
	NSwitch,
	useMessage
} from "naive-ui"
import isIP from "validator/es/lib/isIP"
import isPort from "validator/es/lib/isPort"
import isURL from "validator/es/lib/isURL"
import { computed, onBeforeMount, ref, toRefs, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
	customerCode: string
	customerName: string
	mode?: "new" | "update"
	showDfirIrisUsername?: boolean
}>()

const emit = defineEmits<{
	(e: "update:loading", value: boolean): void
	(e: "submitted", value: CustomerMeta): void
}>()

const { customerCode, customerName, mode, showDfirIrisUsername } = toRefs(props)

const SkipIcon = "carbon:subtract"
const ArrowRightIcon = "carbon:arrow-right"
const ArrowLeftIcon = "carbon:arrow-left"

const loading = ref(false)
const loadingSubscriptions = ref(false)
const loadingDashboards = ref(false)
const loadingDefaultSettings = ref(false)
const message = useMessage()
const current = ref<number>(1)
const currentStatus = ref<StepsProps["status"]>("process")
const form = ref<CustomerProvision>(getClearForm())
const formRef = ref<FormInst | null>(null)

const subscriptionOptions = ref<{ label: string; value: string }[]>([])
const dashboardOptions = ref<{ label: string; value: string }[]>([])

const allDashboardsSelected = computed(
	() => form.value.dashboards_to_include.dashboards.length === dashboardOptions.value.length
)

const isInfrastructureEnabled = computed(() =>
	form.value.customer_subscription.map(o => o.toLowerCase()).includes("wazuh")
)
const isWazuhStepEnabled = computed(() => isInfrastructureEnabled.value && form.value.provision_wazuh_worker)
const isNextStepEnabled = computed(
	() =>
		current.value < 3 ||
		(current.value === 3 && isInfrastructureEnabled.value) ||
		(current.value === 4 && isWazuhStepEnabled.value)
)
const isPrevStepEnabled = computed(() => current.value > 1)
const isSubmitEnabled = computed(
	() =>
		(current.value === 3 && !isInfrastructureEnabled.value) ||
		(current.value === 4 && !isWazuhStepEnabled.value) ||
		(current.value === 5 && isWazuhStepEnabled.value)
)
const slideFormDirection = ref<"right" | "left">("right")

const rules: FormRules = {
	customer_name: {
		required: true,
		message: "Please input Customer Name",
		trigger: ["input", "blur"]
	},
	customer_code: {
		required: true,
		message: "Please input Customer Code",
		trigger: ["input", "blur"]
	},
	customer_grafana_org_name: {
		required: true,
		message: "Please input Customer Grafana.org Name",
		trigger: ["input", "blur"]
	},
	customer_index_name: {
		required: true,
		message: "Please input Customer Index Name",
		trigger: ["input", "blur"]
	},
	customer_subscription: {
		required: true,
		validator: validateAtLeastOne,
		trigger: ["blur"]
	},
	dashboards_to_include: {
		dashboards: {
			required: true,
			validator: validateAtLeastOne,
			trigger: ["blur"]
		}
	},
	wazuh_auth_password: {
		required: true,
		message: "Please input Auth password",
		trigger: ["input", "blur"]
	},
	wazuh_registration_port: {
		required: true,
		validator: validatePort,
		trigger: ["blur"]
	},
	wazuh_logs_port: {
		required: true,
		validator: validatePort,
		trigger: ["blur"]
	},
	wazuh_api_port: {
		required: true,
		validator: validatePort,
		trigger: ["blur"]
	},
	wazuh_cluster_name: {
		required: true,
		message: "Please input Cluster name",
		trigger: ["input", "blur"]
	},
	wazuh_cluster_key: {
		required: true,
		message: "Please input Cluster key",
		trigger: ["input", "blur"]
	},
	wazuh_master_ip: {
		required: true,
		validator: validateIp,
		trigger: ["blur"]
	},
	grafana_url: {
		required: true,
		validator: validateUrl,
		trigger: ["blur"]
	},
	wazuh_worker_hostname: {
		required: true,
		message: "Please input the Wazuh Worker Hostname",
		trigger: ["input", "blur"]
	}
}

function validateUrl(_rule: FormItemRule, value: string) {
	if (!value || !isURL(value, { require_tld: false })) {
		return new Error("Please input a valid URL")
	}

	return true
}

function validatePort(_rule: FormItemRule, value: string) {
	if (!value || !isPort(value)) {
		return new Error("Please input a valid Port number")
	}

	const array: string[] = [form.value.wazuh_registration_port, form.value.wazuh_logs_port, form.value.wazuh_api_port]
	const filled: string[] = array.filter(value => !!value)
	const uniques: string[] = array.filter((value, index, self) => self.indexOf(value) === index)

	if (filled.length === array.length && uniques.length !== array.length) {
		return new Error("Wazuh Ports must all be unique")
	}

	return true
}

function validateIp(_rule: FormItemRule, value: string) {
	if (!value || !isIP(value)) {
		return new Error("Please input a valid IP Address")
	}

	return true
}

function validateAtLeastOne(_rule: FormItemRule, value: string[]) {
	if (!value || !value.length) {
		return new Error("Please select at least one option")
	}

	return true
}

function getClearForm(settings?: CustomerProvisioningDefaultSettings): CustomerProvision {
	return {
		// step1
		customer_code: customerCode.value,
		customer_name: customerName.value,
		customer_grafana_org_name: customerName.value,
		dfir_iris_username: "",

		// step 2
		customer_index_name: "",
		index_replicas: 0,
		index_shards: 1,
		hot_data_retention: 0,

		// step 3
		customer_subscription: ["Wazuh"],
		dashboards_to_include: {
			dashboards: [],
			organizationId: 0, // hide on form
			folderId: 0, // hide on form
			datasourceUid: "uid-to-be-replaced" // hide on form
		},

		// step 4
		provision_ha_proxy: false,
		provision_wazuh_worker: false,

		// step 5
		wazuh_auth_password: "",
		wazuh_registration_port: "",
		wazuh_logs_port: "",
		wazuh_api_port: "",
		wazuh_cluster_name: settings?.cluster_name || "",
		wazuh_cluster_key: settings?.cluster_key || "",
		wazuh_master_ip: settings?.master_ip || "",
		grafana_url: settings?.grafana_url || "",
		wazuh_worker_hostname: settings?.wazuh_worker_hostname || ""
	}
}

function next() {
	validate(() => {
		currentStatus.value = "process"
		slideFormDirection.value = "right"
		current.value++
	})
}

function prev() {
	currentStatus.value = "process"
	slideFormDirection.value = "left"
	current.value--
}

function getProvisioningDefaultSettings() {
	loadingDefaultSettings.value = true

	Api.customers
		.getProvisioningDefaultSettings()
		.then(res => {
			if (res.data.success) {
				setForm(res.data?.customer_provisioning_default_settings)
			}
		})
		.finally(() => {
			loadingDefaultSettings.value = false
		})
}

function getSubscriptions() {
	loadingSubscriptions.value = true

	Api.customers
		.getProvisioningSubscriptions()
		.then(res => {
			if (res.data.success) {
				subscriptionOptions.value = _uniqBy(
					(res.data?.available_subscriptions || []).map(o => ({ label: o, value: o })),
					"value"
				)
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingSubscriptions.value = false
		})
}

function getDashboards() {
	loadingDashboards.value = true

	Api.customers
		.getProvisioningDashboards()
		.then(res => {
			if (res.data.success) {
				dashboardOptions.value = _uniqBy(
					(res.data?.available_dashboards || []).map(o => ({ label: o, value: o })),
					"value"
				)
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingDashboards.value = false
		})
}

function toggleDashboards() {
	if (allDashboardsSelected.value) {
		form.value.dashboards_to_include.dashboards = []
	} else {
		form.value.dashboards_to_include.dashboards = dashboardOptions.value
			.filter(
				o =>
					!["EDR_WAZUH_INVENTORY", "EDR_AGENT_INVENTORY"]
						.map(d => d.toLowerCase())
						.includes(o.value.toLowerCase())
			)
			.map(o => o.value)
	}
}

function validate(cb?: () => void) {
	if (!formRef.value) return

	formRef.value.validate((errors?: Array<FormValidationError>) => {
		if (!errors) {
			if (cb) cb()
		} else {
			message.warning("You must fill in the required fields correctly.")
			return false
		}
	})
}

function reset() {
	currentStatus.value = "process"
	slideFormDirection.value = "right"
	current.value = 1
	setForm()
}

function setForm(settings?: CustomerProvisioningDefaultSettings) {
	form.value = getClearForm(settings)
}

async function submit() {
	currentStatus.value = "finish"
	loading.value = true

	if (mode.value === "update") {
		await Api.customers.decommissionCustomer(customerCode.value)
	}

	Api.customers
		.newCustomerProvision(form.value, customerCode.value)
		.then(res => {
			if (res.data.success) {
				emit("submitted", res.data.customer_meta)
				reset()
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

function generateRandomPassword(length: number = 20): string {
	const uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
	const lowercase = "abcdefghijklmnopqrstuvwxyz"
	const numbers = "0123456789"
	const allChars = uppercase + lowercase + numbers

	let password = ""
	// Ensure at least one of each character type
	password += uppercase[Math.floor(Math.random() * uppercase.length)]
	password += lowercase[Math.floor(Math.random() * lowercase.length)]
	password += numbers[Math.floor(Math.random() * numbers.length)]

	// Fill the rest randomly
	for (let i = password.length; i < length; i++) {
		password += allChars[Math.floor(Math.random() * allChars.length)]
	}

	// Shuffle the password to randomize the guaranteed characters
	return password.split('').sort(() => Math.random() - 0.5).join('')
}

function formPreset(step: number) {
	switch (step) {
		case 2:
			if (!form.value.customer_index_name) {
				form.value.customer_index_name = `wazuh-${form.value.customer_code}`
			}
			break
		case 5:
			if (!form.value.wazuh_auth_password) {
				form.value.wazuh_auth_password = generateRandomPassword()
			}
			break
	}
}

watch(
	() => form.value.provision_wazuh_worker,
	val => {
		if (!val) {
			form.value.provision_ha_proxy = false
		}
	}
)

watch(current, val => {
	formPreset(val)
})

onBeforeMount(() => {
	getProvisioningDefaultSettings()
	getSubscriptions()
	getDashboards()
})
</script>

<style lang="scss" scoped>
.customer-provision-wizard {
	.slide-form-right-enter-active,
	.slide-form-right-leave-active,
	.slide-form-left-enter-active,
	.slide-form-left-leave-active {
		transition: all 0.2s ease-out;
		position: absolute;
		width: 100%;
	}

	.slide-form-left-enter-from {
		transform: translateX(-100%);
	}

	.slide-form-left-leave-to {
		transform: translateX(100%);
	}

	.slide-form-right-enter-from {
		transform: translateX(100%);
	}

	.slide-form-right-leave-to {
		transform: translateX(-100%);
	}
}
</style>
