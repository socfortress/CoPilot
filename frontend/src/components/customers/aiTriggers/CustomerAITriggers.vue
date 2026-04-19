<template>
	<div class="customer-ai-triggers">
		<transition name="form-fade" mode="out-in">
			<div v-if="showForm" class="p-7 pt-4">
				<CustomerAITriggersForm :customer-code @mounted="formCTX = $event" @submitted="refreshList()">
					<template #additionalActions="{ loading: loadingForm }">
						<n-button :disabled="loadingForm" @click="closeForm()">Close</n-button>
					</template>
				</CustomerAITriggersForm>
			</div>
			<div v-else>
				<n-spin :show="loading" class="min-h-48">
					<template v-if="list.length">
						<div class="min-h-52 p-7 pt-4">
							<CustomerAITriggersItem
								v-for="item of list"
								:key="item.id"
								:ai-trigger="item"
								embedded
								class="item-appear item-appear-bottom item-appear-005 mb-2"
								@updated="getAITriggers()"
							/>
						</div>
					</template>
					<template v-else>
						<n-empty v-if="!loading" class="h-48 justify-center">
							<div class="flex flex-col items-center gap-4">
								<p>No AI Trigger found</p>

								<n-button size="small" type="primary" @click="openForm()">
									<template #icon>
										<Icon :name="AddIcon" :size="14" />
									</template>
									Create an AI Trigger
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
import type { AITrigger } from "@/types/incidentManagement/aiTriggers.d"
import { NButton, NEmpty, NSpin, useMessage } from "naive-ui"
import { defineAsyncComponent, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

const { customerCode } = defineProps<{
	customerCode: string
}>()
const CustomerAITriggersItem = defineAsyncComponent(() => import("./CustomerAITriggersItem.vue"))
const CustomerAITriggersForm = defineAsyncComponent(() => import("./CustomerAITriggersForm.vue"))

const AddIcon = "carbon:add-alt"

const message = useMessage()
const showForm = ref(false)
const loading = ref(false)
const list = ref<AITrigger[]>([])
const formCTX = ref<{ reset: (aiTrigger?: AITrigger) => void } | null>(null)

function getAITriggers() {
	loading.value = true

	Api.incidentManagement.aiTriggers
		.getAITriggers(customerCode)
		.then(res => {
			if (res.data.success) {
				list.value = res.data?.ai_triggers || []
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
	getAITriggers()
}

onBeforeMount(() => {
	getAITriggers()
})
</script>

<style lang="scss" scoped>
.customer-ai-triggers {
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
