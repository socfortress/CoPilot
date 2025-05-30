<template>
	<div class="customer-integrations">
		<transition name="form-fade" mode="out-in">
			<div v-if="showForm">
				<CustomerIntegrationForm
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
						Add Integration
					</n-button>
				</div>

				<n-spin :show="loading">
					<div class="min-h-52 p-7 pt-4">
						<template v-if="list.length">
							<CustomerIntegrationItem
								v-for="integration of list"
								:key="integration.id"
								:integration="integration"
								embedded
								class="item-appear item-appear-bottom item-appear-005 mb-2"
								@deployed="refreshList()"
								@deleted="refreshList()"
							/>
						</template>
						<template v-else>
							<n-empty v-if="!loading" description="No integrations found" class="h-48 justify-center" />
						</template>
					</div>
				</n-spin>
			</div>
		</transition>
	</div>
</template>

<script setup lang="ts">
import type { CustomerIntegration } from "@/types/integrations.d"
import { NButton, NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import CustomerIntegrationForm from "./CustomerIntegrationForm.vue"
import CustomerIntegrationItem from "./CustomerIntegrationItem.vue"

const { customerCode, customerName } = defineProps<{
	customerCode: string
	customerName: string
}>()

const AddIcon = "carbon:add-alt"

const message = useMessage()
const showForm = ref(false)
const loading = ref(false)
const list = ref<CustomerIntegration[]>([])
const disabledIds = computed(() => list.value.map(o => o.integration_service_id))

function getCustomerIntegrations() {
	loading.value = true

	Api.integrations
		.getCustomerIntegrations(customerCode)
		.then(res => {
			if (res.data.success) {
				list.value = res.data?.available_integrations || []
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
	getCustomerIntegrations()
}

onBeforeMount(() => {
	getCustomerIntegrations()
})
</script>

<style lang="scss" scoped>
.customer-integrations {
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
