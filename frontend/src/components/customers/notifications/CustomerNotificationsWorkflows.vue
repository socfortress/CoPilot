<template>
	<div class="flex flex-col gap-4">
		<transition name="transition-fade-move" mode="out-in">
			<div v-if="showForm" class="flex flex-col gap-4">
				<h4>Create a Notification</h4>
				<CustomerNotificationsWorkflowsForm ref="formRef" :customer-code @submitted="refreshList()">
					<template #additionalActions="{ loading: loadingForm }">
						<n-button :disabled="loadingForm" @click="closeForm()">Close</n-button>
					</template>
				</CustomerNotificationsWorkflowsForm>
			</div>
			<div v-else class="flex flex-col gap-4">
				<n-spin :show="loading" class="min-h-48">
					<template v-if="list.length">
						<div class="min-h-52">
							<CustomerNotificationsWorkflowsItem
								v-for="item of list"
								:key="item.id"
								:incident-notification="item"
								embedded
								class="item-appear item-appear-bottom item-appear-005 mb-2"
								@updated="getCustomerNetworkConnectors()"
							/>
						</div>
					</template>
					<template v-else>
						<CustomerTabEmpty
							v-if="!loading"
							icon="carbon:flow"
							title="No notification workflow yet"
							description="A notification workflow runs one of your Shuffle workflows for every new alert and case of this customer, with the alert, its asset and the customer passed along: paging, ticketing or a chat message, whatever the workflow does."
							:points="EMPTY_POINTS"
							points-title="How it works"
						>
							<template #actions>
								<n-button type="primary" data-testid="notification-workflow-create" @click="openForm()">
									<template #icon>
										<Icon :name="AddIcon" :size="16" />
									</template>
									Create notification workflow
								</n-button>
							</template>
						</CustomerTabEmpty>
					</template>
				</n-spin>
			</div>
		</transition>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { IncidentNotification } from "@/types/incidentManagement/notifications"
import { NButton, NSpin, useMessage } from "naive-ui"
import { defineAsyncComponent, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import CustomerTabEmpty from "../CustomerTabEmpty.vue"

const { customerCode } = defineProps<{
	customerCode: string
}>()
const CustomerNotificationsWorkflowsItem = defineAsyncComponent(
	() => import("./CustomerNotificationsWorkflowsItem.vue")
)
const CustomerNotificationsWorkflowsForm = defineAsyncComponent(
	() => import("./CustomerNotificationsWorkflowsForm.vue")
)

const AddIcon = "carbon:add-alt"

// What setting this up gives the customer, for the empty tab.
const EMPTY_POINTS = [
	{ title: "Build the workflow in Shuffle", description: "It receives each alert or case and decides what to do with it." },
	{ title: "Paste its id here", description: "One workflow per customer, switched on or off at any time." },
	{ title: "CoPilot runs it", description: "Every new alert and case of this customer triggers it." }
]

const message = useMessage()
const showForm = ref(false)
const loading = ref(false)
const list = ref<IncidentNotification[]>([])
const formRef = ref<{ reset: (incidentNotification?: IncidentNotification) => void } | null>(null)

function getCustomerNetworkConnectors() {
	loading.value = true

	Api.incidentManagement.notification
		.getNotifications(customerCode)
		.then(res => {
			if (res.data.success) {
				list.value = res.data?.notifications || []
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
	formRef.value?.reset()
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
