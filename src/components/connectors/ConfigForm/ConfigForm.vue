<template>generic form</template>

<script setup lang="ts">
import { toRefs } from "vue"
import { Connector } from "@/types/connectors.d"

const props = defineProps<{
    connector: Connector
}>()
const { connector } = toRefs(props)

/*
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
*/
</script>
