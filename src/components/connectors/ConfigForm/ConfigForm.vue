<template>
	<div class="connector-form" v-loading="loading">
		<div class="connector-header">
			<el-image
				class="connector-image"
				fit="contain"
				:src="`/src/assets/images/${
					connector ? connector.connector_name.toLowerCase() + '.svg' : 'default-logo.svg'
				}`"
				:alt="`${connector.connector_name} Logo`"
			>
				<template #placeholder>
					<div class="image-slot">
						<el-icon><icon-picture /></el-icon>
					</div>
				</template>
				<template #error>
					<div class="image-slot">
						<el-icon><icon-picture /></el-icon>
					</div>
				</template>
			</el-image>
			<div class="connector-name">{{ connector.connector_name || "" }}</div>
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

		<div class="connector-footer mt-40">
			<el-form-item>
				<el-button type="primary" @click="saveConnector()">Save</el-button>
				<el-button @click="closeForm(false)">Cancel</el-button>
			</el-form-item>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, toRefs } from "vue"
import { type Connector, type ConnectorForm, ConnectorFormType } from "@/types/connectors.d"
import { Picture as IconPicture } from "@element-plus/icons-vue"
import CredentialsType from "./FormTypes/CredentialsType.vue"
import FileType from "./FormTypes/FileType.vue"
import TokenType from "./FormTypes/TokenType.vue"
import _pick from "lodash/pick"
import { ElMessage, FormInstance } from "element-plus"
import Api from "@/api"

const props = defineProps<{
	connector: Connector
}>()
const { connector } = toRefs(props)

const emit = defineEmits<{
	(e: "close", value: boolean): void
}>()

const connectorForm = ref<ConnectorForm>({
	connector_url: "",
	connector_username: "",
	connector_password: "",
	connector_api_key: "",
	connector_file: null
})
const connectorFormType = computed<ConnectorFormType>(() => getConnectorFormType(connector.value))
const isConnectorConfigured = computed<boolean>(() => connector.value.connector_configured)
const formRef = ref<FormInstance | null>(null)
const loading = ref<boolean>(false)

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

	formRef.value.validate(valid => {
		if (valid) {
			configureConnector()
		} else {
			ElMessage({
				message: "You must fill in the required fields correctly.",
				type: "warning"
			})
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
	if (connectorFormType.value === ConnectorFormType.FILE) {
		const form = new FormData()
		form.append("file", connector_file, connector_file.name)

		requestPayload = form
	}

	requestMethod(connector.value.id, requestPayload)
		.then(() => {
			ElMessage({
				message: "Connector has been successfully configured.",
				type: "success"
			})
			closeForm(true)
		})
		.catch(err => {
			if (err.response.status === 400) {
				if (isConnectorConfigured.value) {
					ElMessage({
						message:
							"This connector is not configured. If you would like to configure this connector select `Configure`.",
						type: "error"
					})
				} else {
					ElMessage({
						message:
							"This connector is already configured. If you would like to reconfigure this connector select `Edit`.",
						type: "error"
					})
				}
			} else if (err.response.status === 401) {
				ElMessage({
					message: "Unauthorized. Please check all fields",
					type: "error"
				})
			} else {
				ElMessage({
					message:
						"Error updating the connector. Your settings were not inserted into the keystore. Please try again.",
					type: "error"
				})
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
		gap: var(--size-4);
		margin-bottom: var(--size-6);

		.connector-image {
			width: var(--size-8);
			height: var(--size-8);
			border: var(--border-size-1) solid var(--gray-1);
			border-radius: var(--radius-round);

			.image-slot {
				display: flex;
				align-items: center;
				justify-content: center;
				width: 100%;
				height: 100%;
			}
		}
		.connector-name {
			font-size: var(--font-size-4);
			font-weight: bold;
		}
	}
}
</style>
