<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Connectors</div>
			<p>Configure connections to your toolset.</p>
		</div>

		<n-card class="table-box" content-style="padding:0">
			<n-spin :show="loading">
				<n-scrollbar x-scrollable style="width: 100%">
					<n-table :bordered="false">
						<thead>
							<tr>
								<th scope="col">Connector Name</th>
								<th scope="col">Connector Description</th>
								<th scope="col">Connector Supports</th>
								<th scope="col">Connector Configured</th>
								<th scope="col">Connector Verified</th>
								<th scope="col">Connector Options</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="connector in connectors" :key="connector.id">
								<!-- Display the connector details in the table -->
								<td>{{ connector.connector_name }}</td>
								<td>{{ connector.connector_description }}</td>
								<td>{{ connector.connector_supports }}</td>
								<td>
									<n-button type="primary" v-if="connector.connector_configured">True</n-button>
									<n-button type="info" v-else>False</n-button>
								</td>
								<!-- Show the connector verified which is in the `connector` table -->
								<td>
									<n-button type="success" v-if="connector.connector_verified">True</n-button>
									<n-button type="error" v-else>False</n-button>
								</td>
								<td>
									<div class="btn-group" role="group">
										<!--If the connector is not already configured then display the configure button -->
										<n-button
											type="primary"
											round
											v-if="!connector.connector_configured"
											@click="openConfigDialog(connector)"
										>
											Configure
										</n-button>

										<n-button type="warning" round v-else @click="openConfigDialog(connector)">
											Update
										</n-button>
										<!--<button type="button" class="btn btn-info btn-sm" @click="deleteConnector(connector)">Delete</button>-->
									</div>
								</td>
							</tr>
						</tbody>
					</n-table>
				</n-scrollbar>
			</n-spin>
		</n-card>

		<n-modal
			title="Connector configuration"
			v-model:show="showConfigDialog"
			:mask-closable="false"
			:close-on-esc="false"
			width="600px"
		>
			<n-card style="width: 90vw; max-width: 500px">
				<ConfigForm v-if="currentConnector" :connector="currentConnector" @close="closeConfigDialog" />
			</n-card>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import Api from "@/api"
import { onBeforeMount, ref } from "vue"
import ConfigForm from "@/components/connectors/ConfigForm"
import { type Connector } from "@/types/connectors.d"
import { NScrollbar, NSpin, NModal, NTable, NButton, NCard } from "naive-ui"

const connectors = ref<Connector[]>([])
const currentConnector = ref<Connector | null>(null)

// Configure Modal
const isConfigureModalActive = ref(false)
const isConfigureModalFileActive = ref(false)

// Update Modal
const isUpdateModalActive = ref(false)

const loading = ref(false)
const showConfigDialog = ref(false)

const successMessage = ref("")
const errorMessage = ref("")
const connectorForm = ref({
	connector_url: "",
	username: "",
	password: "",
	connector_api_key: ""
})

function openConfigDialog(connector: Connector) {
	currentConnector.value = connector
	showConfigDialog.value = true
}
function closeConfigDialog(update: boolean) {
	currentConnector.value = null
	showConfigDialog.value = false

	if (update) {
		getConnectors()
	}
}

function getConnectors() {
	loading.value = true

	Api.connectors
		.getAll()
		.then(res => {
			connectors.value = res.data.connectors
		})
		.catch(err => {
			console.error(err)
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	getConnectors()
})
</script>
