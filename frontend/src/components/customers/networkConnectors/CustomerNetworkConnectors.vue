<template>
	<div class="flex flex-col gap-4">
		<transition name="transition-fade-move" mode="out-in">
			<div v-if="showForm">
				<CustomerNetworkConnectorForm
					:customer-code
					:customer-name
					:disabled-ids-list="disabledIds"
					@submitted="refreshList()"
					@close="closeForm()"
				/>
			</div>
			<div v-else class="flex flex-col gap-4">
				<div v-if="list.length || loading" class="flex items-center justify-between gap-4">
					<n-button size="small" type="primary" @click="openForm()">
						<template #icon>
							<Icon :name="AddIcon" :size="14" />
						</template>
						Add Network Connector
					</n-button>
				</div>

				<n-spin :show="loading">
					<div class="min-h-52">
						<template v-if="list.length">
							<CustomerNetworkConnectorItem
								v-for="networkConnector of list"
								:key="networkConnector.id"
								:network-connector
								embedded
								class="item-appear item-appear-bottom item-appear-005 mb-2"
								@deployed="refreshList()"
								@deleted="refreshList()"
								@decommissioned="refreshList()"
							/>
						</template>
						<template v-else>
							<CustomerTabEmpty
								v-if="!loading"
								icon="carbon:network-3"
								title="No network connectors yet"
								description="Network connectors link this customer's firewalls and network security tools, such as Fortinet, SonicWall or SentinelOne, so their logs reach CoPilot with the rest of the customer's events."
								:points="EMPTY_POINTS"
								points-title="How it works"
							>
								<template #actions>
									<n-button type="primary" data-testid="network-connectors-add" @click="openForm()">
										<template #icon>
											<Icon :name="AddIcon" :size="16" />
										</template>
										Add network connector
									</n-button>
								</template>
							</CustomerTabEmpty>
						</template>
					</div>
				</n-spin>
			</div>
		</transition>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CustomerNetworkConnector } from "@/types/network-connectors"
import { NButton, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import CustomerTabEmpty from "../CustomerTabEmpty.vue"
import CustomerNetworkConnectorForm from "./CustomerNetworkConnectorForm.vue"
import CustomerNetworkConnectorItem from "./CustomerNetworkConnectorItem.vue"

const { customerCode, customerName } = defineProps<{
	customerCode: string
	customerName: string
}>()

const AddIcon = "carbon:add-alt"

// What setting this up gives the customer, for the empty tab.
const EMPTY_POINTS = [
	{ title: "Choose the vendor", description: "The device or service the customer runs." },
	{ title: "Set its keys", description: "The credentials CoPilot uses to reach it, kept for this customer only." },
	{ title: "Deploy it", description: "CoPilot provisions the collection; it can be decommissioned later." }
]

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
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
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
