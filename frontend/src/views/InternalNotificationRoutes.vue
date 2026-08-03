<template>
	<div class="page">
		<div class="mb-4 flex flex-col gap-2">
			<h1>Internal notifications</h1>
			<p class="text-secondary text-sm">
				Where the SOC's own notifications go. These routes belong to no customer — they receive assignment
				events, so telling an analyst that an alert landed on their plate never reaches the customer whose alert
				it was.
				<br />
				For notifications a customer should receive, use
				<strong>Customers → (customer) → Notifications</strong>
				instead.
			</p>
		</div>

		<n-card size="small">
			<transition name="transition-fade" mode="out-in">
				<div v-if="showForm" class="flex flex-col gap-4">
					<h4>{{ editingRoute ? `Edit ${editingRoute.name}` : "Create an internal route" }}</h4>
					<CustomerAiNotificationRouteForm
						:editing-route
						scope="internal"
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
							Add internal route
						</n-button>
					</div>

					<n-spin :show="loading">
						<div class="min-h-48">
							<template v-if="list.length">
								<CustomerAiNotificationRouteItem
									v-for="route of list"
									:key="route.id"
									:route
									scope="internal"
									class="item-appear item-appear-bottom item-appear-005 mb-2"
									@edit="openEdit(route)"
									@deleted="refreshList()"
									@toggled="refreshList()"
								/>
							</template>
							<template v-else>
								<n-empty
									v-if="!loading"
									description="No internal routes yet. Add one to be notified when an alert, case or task is assigned — email can deliver to whoever it was assigned to."
									class="h-48 justify-center"
								/>
							</template>
						</div>
					</n-spin>
				</div>
			</transition>
		</n-card>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { NotificationRoute } from "@/types/notifications"
import { NButton, NCard, NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import CustomerAiNotificationRouteForm from "@/components/customers/aiNotifications/CustomerAiNotificationRoutes/CustomerAiNotificationRouteForm.vue"
import CustomerAiNotificationRouteItem from "@/components/customers/aiNotifications/CustomerAiNotificationRoutes/CustomerAiNotificationRouteItem.vue"
import { getApiErrorMessage } from "@/utils"

// Reuses the per-customer form and item rather than duplicating them. They
// differ in exactly two ways — which triggers apply and which channels are
// possible — which the `scope` prop covers. Duplicating a 700-line form to vary
// two lists would be worse than the prop.

const AddIcon = "carbon:add-alt"

const message = useMessage()
const loading = ref(false)
const list = ref<NotificationRoute[]>([])
const showForm = ref(false)
const editingRoute = ref<NotificationRoute | null>(null)

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

async function refreshList() {
	loading.value = true
	try {
		const res = await Api.notifications.getInternalRoutes()
		if (res.data.success) {
			list.value = res.data.routes
		} else {
			message.warning(res.data.message || "Failed to load internal routes")
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to load internal routes")
	} finally {
		loading.value = false
	}
}

onBeforeMount(() => {
	refreshList()
})
</script>
