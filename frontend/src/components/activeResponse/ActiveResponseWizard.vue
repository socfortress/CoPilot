<template>
	<n-spin :show="loading" class="active-response-wizard">
		<div class="wrapper flex flex-col">
			<div class="grow">
				<n-scrollbar x-scrollable trigger="none">
					<div class="p-7 pt-4">
						<n-steps :current="current" size="small" :status="currentStatus">
							<n-step title="Operative System" />
							<n-step title="Active Response" />
							<n-step title="Submission" />
						</n-steps>
					</div>
				</n-scrollbar>

				<n-form :label-width="80" :model="form" :rules="rules" ref="formRef" class="form-container mt-4">
					<Transition :name="`slide-form-${slideFormDirection}`">
						<div v-if="current === 1" class="px-7 flex flex-col gap-3">
							<div class="os-button">LINUX</div>
							<div class="os-button">WINDOWS</div>
							<div class="os-button">MACOS</div>
						</div>

						<div v-else-if="current === 2" class="px-7 flex flex-col gap-3">
							<div class="list">
								<template v-if="activeResponseList.length">
									<ActiveResponseItem
										v-for="activeResponse of activeResponseList"
										:key="activeResponse.name"
										:activeResponse="activeResponse"
										embedded
										hide-actions
									/>
								</template>
								<template v-else>
									<n-empty
										description="No items found"
										class="justify-center h-48"
										v-if="!loadingActiveResponse"
									/>
								</template>
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
import { computed, ref } from "vue"
import {
	NSteps,
	NStep,
	useMessage,
	NScrollbar,
	NButton,
	NForm,
	NFormItem,
	NSelect,
	NEmpty,
	NSpin,
	type StepsProps,
	type FormRules,
	type FormInst,
	type FormItemRule,
	type FormValidationError
} from "naive-ui"
import type { CustomerMeta, CustomerProvision } from "@/types/customers.d"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import isURL from "validator/es/lib/isURL"
import isPort from "validator/es/lib/isPort"
import isIP from "validator/es/lib/isIP"
import { onBeforeMount } from "vue"
import type { SupportedActiveResponse } from "@/types/activeResponse"
import ActiveResponseItem from "./ActiveResponseItem.vue"

const emit = defineEmits<{
	(e: "update:loading", value: boolean): void
	(e: "submitted", value: CustomerMeta): void
}>()

const ArrowRightIcon = "carbon:arrow-right"
const ArrowLeftIcon = "carbon:arrow-left"

const loading = ref(false)
const loadingSubscriptions = ref(false)
const loadingDashboards = ref(false)
const loadingActiveResponse = ref(false)
const activeResponseList = ref<SupportedActiveResponse[]>([])
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

const isWazuhStepEnabled = computed(() => form.value.customer_subscription.map(o => o.toLowerCase()).includes("wazuh"))
const isNextStepEnabled = computed(() => current.value < 3 || (current.value === 3 && isWazuhStepEnabled.value))
const isPrevStepEnabled = computed(() => current.value > 1)
const isSubmitEnabled = computed(
	() => (current.value === 3 && !isWazuhStepEnabled.value) || (current.value === 4 && isWazuhStepEnabled.value)
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
	if (!value || !isURL(value)) {
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

function getClearForm(): any {
	return {
		// step1
		customer_grafana_org_name: "",

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
		wazuh_cluster_name: "",
		wazuh_cluster_key: "",
		wazuh_master_ip: "",
		grafana_url: ""
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

function getSubscriptions() {
	loadingSubscriptions.value = true

	Api.customers
		.getProvisioningSubscriptions()
		.then(res => {
			if (res.data.success) {
				subscriptionOptions.value = (res.data?.available_subscriptions || []).map(o => ({ label: o, value: o }))
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
				dashboardOptions.value = (res.data?.available_dashboards || []).map(o => ({ label: o, value: o }))
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
}

async function submit() {
	currentStatus.value = "finish"
	loading.value = true

	Api.customers
		.newCustomerProvision(form.value, "")
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

function getAvailableIntegrations() {
	loadingActiveResponse.value = true

	Api.activeResponse
		.getSupported()
		.then(res => {
			if (res.data.success) {
				activeResponseList.value = res.data?.supported_active_responses || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingActiveResponse.value = false
		})
}

onBeforeMount(() => {
	getAvailableIntegrations()
	getSubscriptions()
	getDashboards()
})
</script>

<style lang="scss" scoped>
.active-response-wizard {
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
