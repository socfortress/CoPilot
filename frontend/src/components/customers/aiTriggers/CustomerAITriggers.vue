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
						<CustomerTabEmpty
							v-if="!loading"
							icon="carbon:machine-learning-model"
							title="No AI trigger yet"
							description="An AI trigger has the AI Analyst investigate this customer's alerts on its own: each new alert is handed to it as it arrives, and its report appears on the alert, with no analyst pressing a button."
							:points="EMPTY_POINTS"
							points-title="How it works"
						>
							<template #actions>
								<n-button type="primary" data-testid="ai-trigger-create" @click="openForm()">
									<template #icon>
										<Icon :name="AddIcon" :size="16" />
									</template>
									Create AI trigger
								</n-button>
							</template>
						</CustomerTabEmpty>
					</template>
				</n-spin>
			</div>
		</transition>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { AITrigger } from "@/types/incidentManagement/ai-triggers"
import { NButton, NSpin, useMessage } from "naive-ui"
import { defineAsyncComponent, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import CustomerTabEmpty from "../CustomerTabEmpty.vue"

const { customerCode } = defineProps<{
	customerCode: string
}>()
const CustomerAITriggersItem = defineAsyncComponent(() => import("./CustomerAITriggersItem.vue"))
const CustomerAITriggersForm = defineAsyncComponent(() => import("./CustomerAITriggersForm.vue"))

const AddIcon = "carbon:add-alt"

// What setting this up gives the customer, for the empty tab.
const EMPTY_POINTS = [
	{ title: "Switch it on", description: "One trigger per customer, off until someone turns it on." },
	{ title: "Alerts arrive", description: "Each new alert of this customer is sent to the AI Analyst in the background." },
	{ title: "Reports follow", description: "The findings and IoCs land on the alert for the analysts to review." }
]

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
