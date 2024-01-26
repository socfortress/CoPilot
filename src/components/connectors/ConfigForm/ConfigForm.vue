<template>
	<div class="connector-form">
		<n-spin :show="loading">
			<div class="connector-header">
				<n-avatar
					class="connector-image"
					object-fit="contain"
					round
					:size="60"
					:src="`/src/assets/images/${
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
import { type Connector, type ConnectorForm, ConnectorFormType } from "@/types/connectors.d"
import CredentialsType from "./FormTypes/CredentialsType.vue"
import FileType from "./FormTypes/FileType.vue"
import TokenType from "./FormTypes/TokenType.vue"
import _pick from "lodash/pick"
import { useMessage, NFormItem, NAvatar, NSpin, NButton, type FormInst, type FormValidationError } from "naive-ui"

import Api from "@/api"

const props = defineProps<{
	connector: Connector
}>()
const { connector } = toRefs(props)

const emit = defineEmits<{
	(e: "close", value: boolean): void
	(e: "loading", value: boolean): void
}>()

const message = useMessage()
const connectorForm = ref<ConnectorForm>({
	connector_url: "",
	connector_username: "",
	connector_password: "",
	connector_api_key: "",
	connector_file: null
})
const connectorFormType = computed<ConnectorFormType>(() => getConnectorFormType(connector.value))
const isConnectorConfigured = computed<boolean>(() => connector.value.connector_configured)
const formRef = ref<FormInst | null>(null)
const loading = ref<boolean>(false)

watch(loading, val => {
	emit("loading", val)
})

function setUpForm() {
	connectorForm.value = _pick(connector.value, [
		"connector_url",
		"connector_username",
		"connector_password",
		"connector_api_key",
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
	return ConnectorFormType.UNKNOWN
}

function saveConnector() {
	if (!formRef.value) return

	formRef.value.validate((errors?: Array<FormValidationError>) => {
		if (!errors) {
			configureConnector()
		} else {
			message.warning("You must fill in the required fields correctly.")
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

	const { connector_url, connector_username, connector_password, connector_api_key, connector_file } =
		connectorForm.value

	const requestMethod = getRequestMethod()

	let requestPayload: any = { connector_url }

	if (connectorFormType.value === ConnectorFormType.TOKEN) {
		requestPayload = Object.assign(requestPayload, {
			connector_api_key
		})
	}
	if (connectorFormType.value === ConnectorFormType.CREDENTIALS) {
		requestPayload = Object.assign(requestPayload, {
			connector_username,
			connector_password
		})
	}
	if (connectorFormType.value === ConnectorFormType.FILE && connector_file) {
		const form = new FormData()
		form.append("file", new Blob([connector_file], { type: connector_file.type }), connector_file.name)

		requestPayload = form
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
