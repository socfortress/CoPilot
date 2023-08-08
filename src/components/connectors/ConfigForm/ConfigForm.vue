<template>
    <div class="connector-form">
        <div class="connector-header">
            <el-image
                class="connector-image"
                fit="contain"
                :src="`/src/assets/images/${connector ? connector.connector_name.toLowerCase() + '.svg' : 'default-logo.svg'}`"
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
            <CredentialsType :form="connectorForm" v-if="connectorFormType === ConnectorFormType.CREDENTIALS" />
            <FileType :form="connectorForm" v-if="connectorFormType === ConnectorFormType.FILE" />
            <TokenType :form="connectorForm" v-if="connectorFormType === ConnectorFormType.TOKEN" />
        </div>

        <div class="connector-footer">
            <el-form-item>
                <el-button type="primary" @click="configureConnector">Save</el-button>
                <el-button @click="closeDialogUserandPass">Cancel</el-button>
            </el-form-item>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, ref, toRefs } from "vue"
import { Connector, ConnectorForm, ConnectorFormType } from "@/types/connectors.d"
import { Picture as IconPicture } from "@element-plus/icons-vue"
import CredentialsType from "./FormTypes/CredentialsType.vue"
import FileType from "./FormTypes/FileType.vue"
import TokenType from "./FormTypes/TokenType.vue"

const props = defineProps<{
    connector: Connector
}>()
const { connector } = toRefs(props)

const connectorForm = ref<ConnectorForm>({
    connector_url: "",
    connector_username: "",
    connector_password: "",
    connector_api_key: "",
    connector_file: ""
})
const connectorFormType = computed<ConnectorFormType>(() => getConnectorFormType(connector.value))
const isConnectorConfigured = computed<boolean>(() => connector.value.connector_configured)

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

function configureConnector(event) {
    event.preventDefault()
    const { connector_url, username, password, connector_api_key } = this.connectorForm
    const path = `http://127.0.0.1:5000/connectors/${this.currentConnector.id}`
    this.loading = true
    this.closeDialogUserandPass()

    if (connector_api_key) {
        console.log("POST request to: ", path)
        console.log("Data: ", {
            connector_url: connector_url,
            connector_api_key: connector_api_key
        })
        axios
            .post(path, {
                connector_url: connector_url,
                connector_api_key: connector_api_key
            })
            .then(() => {
                this.successMessage = "Connector has been successfully configured." // Set success message
                setTimeout(() => {
                    this.successMessage = "" // Clear success message after 5 seconds
                }, 5000)
                this.getConnectors() // Refresh the connectors
            })
            .catch(err => {
                if (err.response.status === 400) {
                    this.errorMessage =
                        "This connector is already configured. If you would like to reconfigure this connector select `Edit`." // Set the error message
                } else if (err.response.status === 401) {
                    this.errorMessage = "Unauthorized. Please check your endpoint URL, username and password." // Set the error message
                } else {
                    this.errorMessage = "Error updating the connector. Your settings were not inserted into the keystore. Please try again." // Set the error message
                }
                setTimeout(() => {
                    this.errorMessage = "" // Clear error message after 5 seconds
                }, 5000)
                this.getConnectors() // Refresh the connectors
                console.error(err) // Also log the error for debugging
            })
            .finally(() => {
                this.loading = false // Set loading to false
            })
    } else {
        axios
            .post(path, {
                connector_url: connector_url,
                connector_username: username,
                connector_password: password
            })
            .then(() => {
                this.successMessage = "Connector has been successfully configured." // Set success message
                setTimeout(() => {
                    this.successMessage = "" // Clear success message after 5 seconds
                }, 5000)
                this.getConnectors() // Refresh the connectors
            })
            .catch(err => {
                if (err.response.status === 400) {
                    this.errorMessage =
                        "This connector is already configured. If you would like to reconfigure this connector select `Edit`." // Set the error message
                } else if (err.response.status === 401) {
                    this.errorMessage = "Unauthorized. Please check your endpoint URL, username and password." // Set the error message
                } else {
                    this.errorMessage = "Error updating the connector. Your settings were not inserted into the keystore. Please try again." // Set the error message
                }
                setTimeout(() => {
                    this.errorMessage = "" // Clear error message after 5 seconds
                }, 5000)
                this.getConnectors() // Refresh the connectors
                console.error(err) // Also log the error for debugging
            })
            .finally(() => {
                this.loading = false // Set loading to false
            })
    }
}
function updateConnector(event) {
    event.preventDefault()
    const { connector_url, username, password, connector_api_key } = this.connectorForm
    const path = `http://127.0.0.1:5000/connectors/${this.currentConnector.id}`
    this.loading = true
    this.closeUpdateModal()

    if (connector_api_key) {
        console.log("POST request to: ", path)
        console.log("Data: ", {
            connector_url: connector_url,
            connector_api_key: connector_api_key
        })

        axios
            .put(path, {
                connector_url: connector_url,
                connector_username: username,
                connector_password: password,
                connector_api_key: connector_api_key
            })
            .then(() => {
                this.successMessage = "Connector has been successfully updated." // Set success message
                setTimeout(() => {
                    this.successMessage = "" // Clear success message after 5 seconds
                }, 5000)
                this.getConnectors() // Refresh the connectors
            })
            .catch(err => {
                if (err.response.status === 400) {
                    this.errorMessage =
                        "This connector is not configured. If you would like to configure this connector select `Configure`." // Set the error message
                } else if (err.response.status === 401) {
                    this.errorMessage = "Unauthorized. Please check your endpoint URL, username and password." // Set the error message
                } else {
                    this.errorMessage = "Error updating the connector. Please try again." // Set the error message
                }
                setTimeout(() => {
                    this.errorMessage = "" // Clear error message after 5 seconds
                }, 5000)
                this.getConnectors() // Refresh the connectors
                console.error(err) // Also log the error for debugging
            })
            .finally(() => {
                this.loading = false // Set loading to false
            })
    } else {
        axios
            .put(path, {
                connector_url: connector_url,
                connector_username: username,
                connector_password: password
            })
            .then(() => {
                this.successMessage = "Connector has been successfully updated." // Set success message
                setTimeout(() => {
                    this.successMessage = "" // Clear success message after 5 seconds
                }, 5000)
                this.getConnectors() // Refresh the connectors
            })
            .catch(err => {
                if (err.response.status === 400) {
                    this.errorMessage =
                        "This connector is not configured. If you would like to configure this connector select `Configure`." // Set the error message
                } else if (err.response.status === 401) {
                    this.errorMessage = "Unauthorized. Please check your endpoint URL, username and password." // Set the error message
                } else {
                    this.errorMessage = "Error updating the connector. Please try again." // Set the error message
                }
                setTimeout(() => {
                    this.errorMessage = "" // Clear error message after 5 seconds
                }, 5000)
                this.getConnectors() // Refresh the connectors
                console.error(err) // Also log the error for debugging
            })
            .finally(() => {
                this.loading = false // Set loading to false
            })
    }
}
</script>

<style lang="scss" scoped>
.connector-form {
    .connector-header {
        display: flex;
        align-items: center;
        gap: var(--size-4);
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
