<template>
	<n-spin :show="loading" class="customer-provision-wizard">
		<div class="wrapper flex flex-col">
			<div class="grow">
				<n-scrollbar x-scrollable trigger="none">
					<div class="p-7 pt-4">
						<n-steps :current="current" size="small" :status="currentStatus">
							<n-step title="Provisioning" />
							<n-step title="Graylog" />
							<n-step title="Subscription" />
							<n-step title="Infrastructure">
								<template #icon>
									<Icon :name="SkipIcon" v-if="!isInfrastructureEnabled"></Icon>
								</template>
							</n-step>
							<n-step title="Wazuh Worker">
								<template #icon>
									<Icon :name="SkipIcon" v-if="!isWazuhStepEnabled"></Icon>
								</template>
							</n-step>
						</n-steps>
					</div>
				</n-scrollbar>

				<n-form :label-width="80" :model="form" :rules="rules" ref="formRef" class="form-container mt-4">
					<Transition :name="`slide-form-${slideFormDirection}`">
						<div v-if="current === 1" class="px-7 flex flex-col gap-3">
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
							<n-form-item label="DFIR-IRIS Username" path="dfir_iris_username" class="grow">
								<n-input
									v-model:value.trim="form.dfir_iris_username"
									placeholder="The Username of the API Key CoPilot uses to connect to DFIR-IRIS..."
									clearable
								/>
							</n-form-item>
						</div>

						<div v-else-if="current === 2" class="px-7 flex flex-col gap-3">
							<div class="flex flex-col sm:flex-row gap-3">
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
								<n-form-item label="Hot Data Retention" path="hot_data_retention" class="grow">
									<n-input-number v-model:value="form.hot_data_retention" min="0" class="grow" />
								</n-form-item>
							</div>
						</div>

						<div v-else-if="current === 3" class="px-7 flex flex-col gap-3">
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
									<div class="flex items-center justify-between gap-4 w-full">
										<div>
											Dashboards
											<span class="n-form-item-label__asterisk">*</span>
										</div>
										<div>
											<n-button
												size="tiny"
												v-if="dashboardOptions.length"
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

						<div v-else-if="current === 4" class="px-7 flex gap-3">
							<n-card class="grow">
								<n-form-item label="Deploy HA Proxy" path="provision_ha_proxy">
									<n-switch v-model:value="form.provision_ha_proxy" clearable />
								</n-form-item>
							</n-card>
							<n-card class="grow">
								<n-form-item label="Deploy Wazuh Worker" path="provision_wazuh_worker">
									<n-switch v-model:value="form.provision_wazuh_worker" clearable />
								</n-form-item>
							</n-card>
						</div>

						<div v-else-if="current === 5" class="px-7 flex flex-wrap gap-3">
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
								<n-input v-model:value="form.wazuh_master_ip" placeholder="Master IP..." clearable />
							</n-form-item>
							<n-form-item label="Grafana Url" path="grafana_url" class="grow">
								<n-input v-model:value="form.grafana_url" placeholder="Grafana Url..." clearable />
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
					<n-button @click="prev()" v-if="isPrevStepEnabled">
						<template #icon>
							<Icon :name="ArrowLeftIcon"></Icon>
						</template>
						Prev
					</n-button>
					<n-button @click="next()" v-if="isNextStepEnabled" icon-placement="right">
						<template #icon>
							<Icon :name="ArrowRightIcon"></Icon>
						</template>
						Next
					</n-button>
					<n-button type="primary" @click="validate(submit)" :loading="loading" v-if="isSubmitEnabled">
						Submit
					</n-button>
				</div>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import { computed, ref, toRefs } from "vue"
import {
	NSteps,
	NStep,
	useMessage,
	NScrollbar,
	NButton,
	NForm,
	NFormItem,
	NInput,
	NSelect,
	NInputNumber,
	NSpin,
	NSwitch,
	NCard,
	type StepsProps,
	type FormRules,
	type FormInst,
	type FormItemRule,
	type FormValidationError
} from "naive-ui"
import type { CustomerMeta, CustomerProvision, CustomerProvisioningDefaultSettings } from "@/types/customers.d"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import isURL from "validator/es/lib/isURL"
import isPort from "validator/es/lib/isPort"
import isIP from "validator/es/lib/isIP"
import { onBeforeMount } from "vue"
import _uniqBy from "lodash/uniqBy"

const emit = defineEmits<{
	(e: "update:loading", value: boolean): void
	(e: "submitted", value: CustomerMeta): void
}>()

const props = defineProps<{
	customerCode: string
	customerName: string
	mode?: "new" | "update"
}>()
const { customerCode, customerName, mode } = toRefs(props)

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
	}
}

function validateUrl(rule: FormItemRule, value: string) {
	if (!value || !isURL(value, { require_tld: false })) {
		return new Error("Please input a valid URL")
	}

	return true
}

function validatePort(rule: FormItemRule, value: string) {
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

function validateIp(rule: FormItemRule, value: string) {
	if (!value || !isIP(value)) {
		return new Error("Please input a valid IP Address")
	}

	return true
}

function validateAtLeastOne(rule: FormItemRule, value: string[]) {
	if (!value || !value.length) {
		return new Error("Please select at least one option")
	}

	return true
}

function getClearForm(settings?: CustomerProvisioningDefaultSettings): CustomerProvision {
	return {
		// step1
		customer_name: customerName.value,
		customer_code: customerCode.value,
		customer_grafana_org_name: "",
		dfir_iris_username: "",

		// step 2
		customer_index_name: "",
		hot_data_retention: 0,
		index_replicas: 0,
		index_shards: 1,

		// step 3
		customer_subscription: ["Wazuh"],
		dashboards_to_include: {
			dashboards: [],
			organizationId: 0, // hide on form
			folderId: 0, // hide on form
			datasourceUid: "uid-to-be-replaced" // hide on form
		},

		// step 4
		wazuh_auth_password: "",
		wazuh_registration_port: "",
		wazuh_logs_port: "",
		wazuh_api_port: "",
		wazuh_cluster_name: settings?.cluster_name || "",
		wazuh_cluster_key: settings?.cluster_key || "",
		wazuh_master_ip: settings?.master_ip || "",
		grafana_url: settings?.grafana_url || "",
		provision_wazuh_worker: false,
		provision_ha_proxy: false
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
		form.value.dashboards_to_include.dashboards = dashboardOptions.value.map(o => o.value)
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

onBeforeMount(() => {
	getProvisioningDefaultSettings()
	getSubscriptions()
	getDashboards()
})
</script>

<style lang="scss" scoped>
.customer-provision-wizard {
	.wrapper {
		min-height: 480px;
	}

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
