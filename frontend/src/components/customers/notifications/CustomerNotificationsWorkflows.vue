<template>
	<div class="customer-notifications-workflows flex flex-col gap-4">
		<transition name="form-fade" mode="out-in">
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
						<n-empty v-if="!loading" class="h-48 justify-center">
							<div class="flex flex-col items-center gap-4">
								<p>No Notification found</p>

								<n-button size="small" type="primary" @click="openForm()">
									<template #icon>
										<Icon :name="AddIcon" :size="14" />
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
import type { ApiError } from "@/types/common"
import type { IncidentNotification } from "@/types/incidentManagement/notifications.d"
import { NButton, NEmpty, NSpin, useMessage } from "naive-ui"
import { defineAsyncComponent, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

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

<style lang="scss" scoped>
.customer-notifications-workflows {
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
