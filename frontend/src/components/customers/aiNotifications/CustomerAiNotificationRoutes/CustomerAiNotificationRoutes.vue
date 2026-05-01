<template>
	<div class="customer-ai-notification-routes flex flex-col gap-4">
		<transition name="fade" mode="out-in">
			<div v-if="showForm" class="flex flex-col gap-4">
				<h4>Create a notification route</h4>
				<CustomerAiNotificationRouteForm
					:customer-code
					:editing-route
					@submitted="onFormSubmitted"
					@close="closeForm()"
				/>
			</div>
			<div v-else class="flex flex-col gap-4">
				<div class="flex items-center justify-between gap-4">
					<n-button size="small" type="primary" @click="openForm()">
						<template #icon>
							<Icon :name="AddIcon" :size="14" />
						</template>
						Add route
					</n-button>
				</div>

				<n-spin :show="loading">
					<div class="min-h-52">
						<template v-if="list.length">
							<CustomerAiNotificationRouteItem
								v-for="route of list"
								:key="route.id"
								:route
								class="item-appear item-appear-bottom item-appear-005 mb-2"
								@edit="openEdit(route)"
								@deleted="refreshList()"
								@toggled="refreshList()"
							/>
						</template>
						<template v-else>
							<n-empty
								v-if="!loading"
								description="No routes configured. Add one to send Talon's investigation summaries to Slack or email."
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
import type { NotificationRoute } from "@/types/notifications.d"
import { NButton, NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import CustomerAiNotificationRouteForm from "./CustomerAiNotificationRouteForm.vue"
import CustomerAiNotificationRouteItem from "./CustomerAiNotificationRouteItem.vue"

const { customerCode } = defineProps<{
	customerCode: string
}>()

const AddIcon = "carbon:add-alt"

const message = useMessage()
const showForm = ref(false)
const loading = ref(false)
const list = ref<NotificationRoute[]>([])
const editingRoute = ref<NotificationRoute | null>(null)

function refreshList() {
	loading.value = true
	Api.notifications
		.listRoutes(customerCode)
		.then(res => {
			if (res.data.success) {
				list.value = res.data.routes
			} else {
				message.warning(res.data.message || "Failed to load routes")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err) || "Failed to load routes")
		})
		.finally(() => {
			loading.value = false
		})
}

function openForm() {
	editingRoute.value = null
	showForm.value = true
}

function openEdit(route: NotificationRoute) {
	editingRoute.value = route
	showForm.value = true
}

function closeForm() {
	showForm.value = false
	editingRoute.value = null
}

function onFormSubmitted() {
	closeForm()
	refreshList()
}

onBeforeMount(refreshList)
</script>

<style lang="scss" scoped>
.fade-enter-active,
.fade-leave-active {
	transition: opacity 0.2s ease-in-out;
}
.fade-enter-from,
.fade-leave-to {
	opacity: 0;
}
</style>
