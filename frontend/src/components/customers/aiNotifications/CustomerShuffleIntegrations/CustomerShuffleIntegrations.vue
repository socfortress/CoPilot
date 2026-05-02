<template>
	<div class="customer-shuffle-integrations">
		<transition name="form-fade" mode="out-in">
			<div v-if="showForm">
				<CustomerShuffleIntegrationForm
					:customer-code
					:editing-integration
					@submitted="onFormSubmitted"
					@close="closeForm()"
				/>
			</div>
			<div v-else>
				<div class="flex items-center justify-between gap-4 px-7 pt-2">
					<n-button size="small" type="primary" @click="openForm()">
						<template #icon>
							<Icon :name="AddIcon" :size="14" />
						</template>
						Add Shuffle integration
					</n-button>
					<n-button size="small" :disabled="loading" @click="refreshList()">
						<template #icon>
							<Icon :name="RefreshIcon" :size="14" />
						</template>
						Refresh
					</n-button>
				</div>

				<div class="text-secondary px-7 pt-2 text-sm">
					Each row is one of this customer's Shuffle organizations. Routes set to the
					<strong>Shuffle</strong> channel reference one of these to pick the right org
					for outbound notifications. The deployment-wide Shuffle API key lives in the
					CoPilot connectors table — these rows just record the per-customer Org-Id.
				</div>

				<n-spin :show="loading">
					<div class="min-h-52 p-7 pt-4">
						<template v-if="list.length">
							<CustomerShuffleIntegrationItem
								v-for="integration of list"
								:key="integration.id"
								:integration="integration"
								class="item-appear item-appear-bottom item-appear-005 mb-2"
								@edit="openEdit(integration)"
								@deleted="refreshList()"
								@toggled="refreshList()"
							/>
						</template>
						<template v-else>
							<n-empty
								v-if="!loading"
								description="No Shuffle integrations configured. Add one to enable Shuffle-channel notification routes for this customer."
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
import type { ShuffleIntegration } from "@/types/notifications.d"
import { NButton, NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import CustomerShuffleIntegrationForm from "./CustomerShuffleIntegrationForm.vue"
import CustomerShuffleIntegrationItem from "./CustomerShuffleIntegrationItem.vue"

const { customerCode } = defineProps<{
	customerCode: string
}>()

const AddIcon = "carbon:add-alt"
const RefreshIcon = "carbon:renew"

const message = useMessage()
const showForm = ref(false)
const loading = ref(false)
const list = ref<ShuffleIntegration[]>([])
const editingIntegration = ref<ShuffleIntegration | null>(null)

function refreshList() {
	loading.value = true
	Api.notifications
		.listShuffleIntegrations(customerCode)
		.then(res => {
			if (res.data.success) {
				list.value = res.data.integrations
			} else {
				message.warning(res.data.message || "Failed to load Shuffle integrations")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err) || "Failed to load Shuffle integrations")
		})
		.finally(() => {
			loading.value = false
		})
}

function openForm() {
	editingIntegration.value = null
	showForm.value = true
}

function openEdit(integration: ShuffleIntegration) {
	editingIntegration.value = integration
	showForm.value = true
}

function closeForm() {
	showForm.value = false
	editingIntegration.value = null
}

function onFormSubmitted() {
	closeForm()
	refreshList()
}

onBeforeMount(refreshList)
</script>
