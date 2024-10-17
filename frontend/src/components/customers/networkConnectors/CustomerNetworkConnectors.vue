<template>
	<div class="customer-network-connectors">
		<transition name="form-fade" mode="out-in">
			<div v-if="showForm">
				<CustomerNetworkConnectorForm
					:customer-code="customerCode"
					:customer-name="customerName"
					:disabled-ids-list="disabledIds"
					@submitted="refreshList()"
					@close="closeForm()"
				/>
			</div>
			<div v-else>
				<div class="flex items-center justify-between gap-4 px-7 pt-2">
					<n-button size="small" type="primary" @click="openForm()">
						<template #icon>
							<Icon :name="AddIcon" :size="14"></Icon>
						</template>
						Add Network Connector
					</n-button>
				</div>

				<n-spin :show="loading">
					<div class="list p-7 pt-4">
						<template v-if="list.length">
							<CustomerNetworkConnectorItem
								v-for="networkConnector of list"
								:key="networkConnector.id"
								:network-connector="networkConnector"
								embedded
								class="item-appear item-appear-bottom item-appear-005 mb-2"
								@deployed="refreshList()"
								@deleted="refreshList()"
								@decommissioned="refreshList()"
							/>
						</template>
						<template v-else>
							<n-empty
								v-if="!loading"
								description="No network connectors found"
								class="h-48 justify-center"
							/>
						</template>
					</div>
				</n-spin>
			</div>
		</transition>
	</div>
</template>

<script setup lang="ts">
import type { CustomerNetworkConnector } from "@/types/networkConnectors.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { NButton, NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import CustomerNetworkConnectorForm from "./CustomerNetworkConnectorForm.vue"
import CustomerNetworkConnectorItem from "./CustomerNetworkConnectorItem.vue"

const { customerCode, customerName } = defineProps<{
	customerCode: string
	customerName: string
}>()

const AddIcon = "carbon:add-alt"

const message = useMessage()
const showForm = ref(false)
const loading = ref(false)
const list = ref<CustomerNetworkConnector[]>([])
const disabledIds = computed(() => list.value.map(o => o.network_connector_service_id))

function getCustomerNetworkConnectors() {
	loading.value = true

	Api.networkConnectors
		.getCustomerNetworkConnectors(customerCode)
		.then(res => {
			if (res.data.success) {
				list.value = res.data?.available_network_connectors || []
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

function openForm() {
	showForm.value = true
}

function closeForm() {
	showForm.value = false
}

function refreshList() {
	closeForm()
	getCustomerNetworkConnectors()
}

onBeforeMount(() => {
	getCustomerNetworkConnectors()
})
</script>

<style lang="scss" scoped>
.customer-network-connectors {
	.list {
		container-type: inline-size;
		min-height: 200px;
	}

	.form-fade-enter-active,
	.form-fade-leave-active {
		transition:
			opacity 0.2s ease-in-out,
			transform 0.3s ease-in-out;
	}
	.form-fade-enter-from {
		opacity: 0;
		transform: translateY(10px);
	}
	.form-fade-leave-to {
		opacity: 0;
		transform: translateY(-10px);
	}
}
</style>
