<template>
	<div class="customer-ai-notification-routes flex flex-col gap-4">
		<transition name="transition-fade" mode="out-in">
			<div v-if="showForm" class="flex flex-col gap-4">
				<h4>{{ editingRoute ? `Edit ${editingRoute.name}` : "Create a notification route" }}</h4>
				<CustomerAiNotificationRouteForm
					:customer-code
					:editing-route
					@submitted="onFormSubmitted"
					@close="closeForm()"
				/>
			</div>
			<div v-else class="flex flex-col gap-4">
				<div v-if="list.length || loading" class="flex items-center justify-between gap-4">
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
								:customer-code
								class="item-appear item-appear-bottom item-appear-005 mb-2"
								@edit="openEdit(route)"
								@deleted="refreshList()"
								@toggled="refreshList()"
							/>
						</template>
						<template v-else>
							<CustomerTabEmpty
								v-if="!loading"
								icon="carbon:send-alt"
								title="No notification routes yet"
								description="A route sends this customer's events, such as the AI Analyst's investigation summaries, to a Shuffle app or straight to a webhook: an automation platform, a chat channel or an endpoint of your own."
								:points="EMPTY_POINTS"
								points-title="How it works"
							>
								<template #actions>
									<n-button type="primary" data-testid="notification-routes-add" @click="openForm()">
										<template #icon>
											<Icon :name="AddIcon" :size="16" />
										</template>
										Add route
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
import type { NotificationRoute } from "@/types/notifications"
import { NButton, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import CustomerTabEmpty from "../../CustomerTabEmpty.vue"
import CustomerAiNotificationRouteForm from "./CustomerAiNotificationRouteForm.vue"
import CustomerAiNotificationRouteItem from "./CustomerAiNotificationRouteItem.vue"

const { customerCode } = defineProps<{
	customerCode: string
}>()

const AddIcon = "carbon:add-alt"

// What setting this up gives the customer, for the empty tab.
const EMPTY_POINTS = [
	{ title: "Pick the events", description: "Which triggers the route listens to, and from which severity up." },
	{ title: "Pick the channel", description: "A Shuffle app of the customer's organization, or a direct webhook." },
	{ title: "Shape the message", description: "A template decides what is sent; every dispatch is kept in the log." }
]

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
