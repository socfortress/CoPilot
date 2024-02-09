<template>
	<div class="connector-form">
		<n-spin :show="loading">
			<div class="connector-header">
				<n-avatar
					class="connector-image"
					object-fit="contain"
					round
					:size="60"
					:src="`/images/connectors/${
						connector ? connector.connector_name.toLowerCase() + '.svg' : 'default-logo.svg'
					}`"
					:alt="`${connector.connector_name} Logo`"
					fallback-src="/images/img-not-found.svg"
				/>

				<h3>{{ connector.connector_name || "" }}</h3>
			</div>

			<div class="connector-form-type">
				<CredentialsType
					:form="connectorForm"
					v-if="connectorFormType === ConnectorFormType.CREDENTIALS"
					@mounted="formRef = $event"
				/>
				<FileType
					:form="connectorForm"
					v-if="connectorFormType === ConnectorFormType.FILE"
					@mounted="formRef = $event"
				/>
				<TokenType
					:form="connectorForm"
					v-if="connectorFormType === ConnectorFormType.TOKEN"
					@mounted="formRef = $event"
				/>
				<HostType
					:form="connectorForm"
					v-if="connectorFormType === ConnectorFormType.HOST"
					@mounted="formRef = $event"
				/>
			</div>
			<div class="connector-form-options">
				<n-form
					:model="connectorForm"
					:rules="optionsRules"
					label-width="120px"
					ref="formOptionsRef"
					label-placement="top"
				>
					<n-form-item label="Extra data" path="connector_extra_data" v-if="connectorFormOptions.extraData">
						<n-input v-model:value="connectorForm.connector_extra_data" type="text" />
					</n-form-item>
				</n-form>
			</div>

			<div class="connector-footer mt-4">
				<n-form-item>
					<div class="flex gap-2 justify-end w-full">
						<n-button type="primary" @click="saveConnector()">Save</n-button>
						<n-button @click="closeForm(false)">Cancel</n-button>
					</div>
				</n-form-item>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, toRefs, watch } from "vue"
import {
	ConnectorFormType,
	type Connector,
	type ConnectorForm,
	type ConnectorRequestPayload,
	type ConnectorFormOptions,
	type ConnectorFormOptionKeys
} from "@/types/connectors.d"
import CredentialsType from "./FormTypes/CredentialsType.vue"
import FileType from "./FormTypes/FileType.vue"
import TokenType from "./FormTypes/TokenType.vue"
import HostType from "./FormTypes/HostType.vue"
import _pick from "lodash/pick"
import {
	useMessage,
	NFormItem,
	NAvatar,
	NSpin,
	NForm,
	NInput,
	NButton,
	type FormInst,
	type FormValidationError,
	type FormRules
} from "naive-ui"
import Api from "@/api"

const props = defineProps<{
	connector: Connector
}>()
const { connector } = toRefs(props)

const emit = defineEmits<{
	(e: "close", value: boolean): void
	(e: "loading", value: boolean): void
}>()

const connectorForm = ref<ConnectorForm>({
	connector_url: "",
	connector_username: "",
	connector_password: "",
	connector_api_key: "",
	connector_extra_data: "",
	connector_file: null
})

const optionsRules: FormRules = {
	connector_extra_data: [{ required: true, trigger: "blur", message: "Please input a valid Extra Data" }]
}

const message = useMessage()
const formOptionsRef = ref<FormInst>()
const connectorFormType = computed<ConnectorFormType>(() => getConnectorFormType(connector.value))
const connectorFormOptions = computed<ConnectorFormOptions>(() => getConnectorFormOptions(connector.value))
const isConnectorConfigured = computed<boolean>(() => connector.value.connector_configured)
const formRef = ref<FormInst | null>(null)
const loading = ref<boolean>(false)

const formOptionsCheckRequired = computed<boolean>(() => {
	let checkRequired = false
	for (const key in connectorFormOptions.value) {
		const required = connectorFormOptions.value[key as ConnectorFormOptionKeys]
		if (required === true) {
			checkRequired = true
		}
	}
	return checkRequired
})

watch(loading, val => {
	emit("loading", val)
})

function setUpForm() {
	connectorForm.value = _pick(connector.value, [
		"connector_url",
		"connector_username",
		"connector_password",
		"connector_api_key",
		"connector_extra_data",
		"connector_file"
	]) as unknown as ConnectorForm
}

function getConnectorFormType(connector: Connector): ConnectorFormType {
	if (connector.connector_accepts_api_key) {
		return ConnectorFormType.TOKEN
	}
	if (connector.connector_accepts_file) {
		return ConnectorFormType.FILE
	}
	if (connector.connector_accepts_username_password) {
		return ConnectorFormType.CREDENTIALS
	}
	if (connector.connector_accepts_host_only) {
		return ConnectorFormType.HOST
	}
	return ConnectorFormType.UNKNOWN
}

function getConnectorFormOptions(connector: Connector): ConnectorFormOptions {
	const options: ConnectorFormOptions = {}

	if (connector.connector_accepts_extra_data) {
		options.extraData = true
	}

	return options
}

function saveConnector() {
	if (!formRef.value) return

	let messageSent = false

	formRef.value.validate((errors?: Array<FormValidationError>) => {
		if (!errors) {
			if (formOptionsRef.value && formOptionsCheckRequired.value) {
				formOptionsRef.value.validate((errors?: Array<FormValidationError>) => {
					if (!errors) {
						configureConnector()
					} else {
						if (!messageSent) {
							message.warning("You must fill in the required fields correctly.")
						}
						return false
					}
				})
			} else {
				configureConnector()
			}
		} else {
			message.warning("You must fill in the required fields correctly.")
			messageSent = true
			return false
		}
	})
}

function closeForm(update: boolean) {
	emit("close", update)
}

function getRequestMethod() {
	if (connectorFormType.value === ConnectorFormType.FILE) {
		return Api.connectors.upload
	}

	return isConnectorConfigured.value ? Api.connectors.update : Api.connectors.configure
}

function configureConnector() {
	loading.value = true

	const {
		connector_url,
		connector_username,
		connector_password,
		connector_api_key,
		connector_file,
		connector_extra_data
	} = connectorForm.value

	const requestMethod = getRequestMethod()

	let requestPayload: ConnectorRequestPayload = {}

	if (connectorFormType.value === ConnectorFormType.HOST) {
		requestPayload = {
			connector_url
		}
	}
	if (connectorFormType.value === ConnectorFormType.TOKEN) {
		requestPayload = {
			connector_url,
			connector_api_key
		}
	}
	if (connectorFormType.value === ConnectorFormType.CREDENTIALS) {
		requestPayload = {
			connector_url,
			connector_username,
			connector_password
		}
	}
	if (connectorFormType.value === ConnectorFormType.FILE && connector_file) {
		const form = new FormData()
		form.append("file", new Blob([connector_file], { type: connector_file.type }), connector_file.name)
		requestPayload = form
	}
	if (connectorFormOptions.value.extraData) {
		if (requestPayload instanceof FormData) {
			requestPayload.append("connector_extra_data", connector_extra_data)
		} else {
			requestPayload.connector_extra_data = connector_extra_data
		}
	}

	requestMethod(connector.value.id, requestPayload)
		.then(() => {
			message.success("Connector has been successfully configured.")
			closeForm(true)
		})
		.catch(err => {
			if (err.response.status === 400) {
				if (isConnectorConfigured.value) {
					message.error(
						"This connector is not configured. If you would like to configure this connector select `Configure`."
					)
				} else {
					message.error(
						"This connector is already configured. If you would like to reconfigure this connector select `Edit`."
					)
				}
			} else if (err.response?.status === 401) {
				message.error("Unauthorized. Please check all fields")
			} else {
				message.error(
					"Error updating the connector. Your settings were not inserted into the keystore. Please try again."
				)
			}
			closeForm(false)
		})
		.finally(() => {
			loading.value = false
		})
}

onMounted(() => {
	setUpForm()
})
</script>

<style lang="scss" scoped>
.connector-form {
	.connector-header {
		display: flex;
		align-items: center;
		@apply gap-5 mb-7;

		.connector-image {
			border: 2px solid var(--bg-body);
		}
	}
}
</style>
