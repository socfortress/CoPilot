<template>
	<div class="customer-integrations">
		<transition name="form-fade" mode="out-in">
			<div v-if="showForm">
				<CustomerIntegrationForm
					:customerCode="customerCode"
					:customerName="customerName"
					:disabledIdsList="disabledIds"
					@submitted="refreshList()"
					@close="closeForm()"
				/>
			</div>
			<div v-else>
				<div class="flex items-center justify-between gap-4 px-7 pt-2">
					<n-button size="small" @click="openForm()" type="primary">
						<template #icon>
							<Icon :name="AddIcon" :size="14"></Icon>
						</template>
						Add Integration
					</n-button>
				</div>

				<n-spin :show="loading">
					<div class="list p-7 pt-4">
						<template v-if="list.length">
							<CustomerIntegrationItem
								v-for="integration of list"
								:key="integration.id"
								:integration="integration"
								@deployed="refreshList()"
								@deleted="refreshList()"
								embedded
								class="item-appear item-appear-bottom item-appear-005 mb-2"
							/>
						</template>
						<template v-else>
							<n-empty description="No integrations found" class="justify-center h-48" v-if="!loading" />
						</template>
					</div>
				</n-spin>
			</div>
		</transition>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, computed } from "vue"
import { useMessage, NSpin, NEmpty, NButton } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import CustomerIntegrationForm from "./CustomerIntegrationForm.vue"
import CustomerIntegrationItem from "./CustomerIntegrationItem.vue"
import type { CustomerIntegration } from "@/types/integrations.d"

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
