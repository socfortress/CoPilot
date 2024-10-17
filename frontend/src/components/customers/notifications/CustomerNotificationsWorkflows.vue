<template>
	<div class="customer-notifications-workflows">
		<transition name="form-fade" mode="out-in">
			<div v-if="showForm" class="p-7 pt-4">
				<CustomerNotificationsWorkflowsForm
					:customer-code
					@mounted="formCTX = $event"
					@submitted="refreshList()"
				>
					<template #additionalActions="{ loading: loadingForm }">
						<n-button :disabled="loadingForm" @click="closeForm()">Close</n-button>
					</template>
				</CustomerNotificationsWorkflowsForm>
			</div>
			<div v-else>
				<n-spin :show="loading" class="min-h-48">
					<template v-if="list.length">
						<div class="list p-7 pt-4">
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
						<n-empty v-if="!loading" class="h-48 justify-center">
							<div class="flex flex-col items-center gap-4">
								<p>No Notification found</p>

								<n-button size="small" type="primary" @click="openForm()">
									<template #icon>
										<Icon :name="AddIcon" :size="14"></Icon>
									</template>
									Create a Notification
								</n-button>
							</div>
						</n-empty>
					</template>
				</n-spin>
			</div>
		</transition>
	</div>
</template>

<script setup lang="ts">
import type { IncidentNotification } from "@/types/incidentManagement/notifications.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { NButton, NEmpty, NSpin, useMessage } from "naive-ui"
import { defineAsyncComponent, onBeforeMount, ref } from "vue"

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

const message = useMessage()
const showForm = ref(false)
const loading = ref(false)
const list = ref<IncidentNotification[]>([])
const formCTX = ref<{ reset: (incidentNotification?: IncidentNotification) => void } | null>(null)

function getCustomerNetworkConnectors() {
	loading.value = true

	Api.incidentManagement
		.getNotifications(customerCode)
		.then(res => {
			if (res.data.success) {
				list.value = res.data?.notifications || []
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
.customer-notifications-workflows {
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
