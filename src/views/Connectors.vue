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
								<th scope="col" style="width: 190px" class="!text-center">Connector Configured</th>
								<th scope="col" style="width: 170px" class="!text-center">Connector Verified</th>
								<th scope="col" style="width: 170px" class="!text-right">Connector Options</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="connector in connectors" :key="connector.id">
								<!-- Display the connector details in the table -->
								<td>{{ connector.connector_name }}</td>
								<td>{{ connector.connector_description || "-" }}</td>
								<td style="width: 190px" class="text-center">
									<strong
										class="flag-field"
										:class="{
											success: connector.connector_configured,
											warning: !connector.connector_configured
										}"
									>
										{{ connector.connector_configured ? "Yes" : "No" }}
									</strong>
								</td>
								<!-- Show the connector verified which is in the `connector` table -->
								<td style="width: 170px" class="text-center">
									<strong
										class="flag-field"
										:class="{
											success: connector.connector_verified,
											warning: !connector.connector_verified
										}"
									>
										{{ connector.connector_verified ? "Yes" : "No" }}
									</strong>
								</td>
								<td style="width: 170px">
									<div class="flex justify-end items-center gap-3">
										<!--If the connector is not already configured then display the configure button -->
										<n-button
											type="primary"
											v-if="!connector.connector_configured"
											@click="openConfigDialog(connector)"
										>
											Configure
										</n-button>

										<n-button v-else @click="openConfigDialog(connector)">Update</n-button>
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

const loading = ref(false)
const showConfigDialog = ref(false)

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

<style scoped lang="scss">
.table-box {
	.flag-field {
		&.success {
			color: var(--success-color);
		}
		&.warning {
			color: var(--warning-color);
		}
	}

	tr:hover {
		td {
			background-color: var(--primary-005-color);
		}
	}
}
</style>
