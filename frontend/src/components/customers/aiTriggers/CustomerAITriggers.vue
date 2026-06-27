<template>
	<div class="flex flex-col gap-4">
		<transition name="transition-fade-move" mode="out-in">
			<div v-if="showForm" class="flex flex-col gap-4">
				<h4>Create an AI Trigger</h4>
				<CustomerAITriggersForm ref="formRef" :customer-code @submitted="refreshList()">
					<template #additionalActions="{ loading: loadingForm }">
						<n-button :disabled="loadingForm" @click="closeForm()">Close</n-button>
					</template>
				</CustomerAITriggersForm>
			</div>
			<div v-else class="flex flex-col gap-4">
				<n-spin :show="loading" class="min-h-48">
					<template v-if="list.length">
						<div class="min-h-52">
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
import type { ApiError } from "@/types/common"
import type { AITrigger } from "@/types/incidentManagement/ai-triggers"
import { NButton, NEmpty, NSpin, useMessage } from "naive-ui"
import { defineAsyncComponent, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

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
const formRef = ref<{ reset: (aiTrigger?: AITrigger) => void } | null>(null)

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
	getAITriggers()
}

onBeforeMount(() => {
	getAITriggers()
})
</script>
