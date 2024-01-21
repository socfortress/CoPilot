<template>
	<div class="customer-integration-form flex flex-col gap-4">
		<div>
			<n-scrollbar x-scrollable trigger="none">
				<div class="px-7 pt-4 pb-2">
					<n-steps :current="current" size="small" :status="currentStatus">
						<n-step title="Choose Integration" />
						<n-step title="Set Auth Keys">
							<template #icon>
								<Icon :name="SkipIcon" v-if="!isWazuhStepEnabled"></Icon>
							</template>
						</n-step>
					</n-steps>
				</div>
			</n-scrollbar>
		</div>

		<div class="flex flex-col grow overflow-hidden">
			<Transition :name="`slide-form-${slideFormDirection}`">
				<div class="available-list grow overflow-hidden" v-if="current === 1">
					<n-scrollbar style="max-height: 100%" trigger="none">
						<IntegrationsList embedded hide-totals class="px-7" />
					</n-scrollbar>
				</div>
				<div class="auth-key-form" v-else>auth-key-form</div>
			</Transition>
		</div>

		<div class="flex justify-between gap-4 px-7">
			<div class="flex gap-4">
				<n-button @click="emit('close')">Close</n-button>
			</div>
			<div class="flex gap-4">
				<n-button @click="prev()" v-if="isPrevStepEnabled">
					<template #icon>
						<Icon :name="ArrowLeftIcon"></Icon>
					</template>
					Prev
				</n-button>
				<n-button @click="next()" v-if="isNextStepEnabled" icon-placement="right">
					<template #icon>
						<Icon :name="ArrowRightIcon"></Icon>
					</template>
					Next
				</n-button>
				<n-button type="primary" @click="validate()" :loading="loading" v-if="isSubmitEnabled">
					<template #icon>
						<Icon :name="AddIcon" :size="14"></Icon>
					</template>
					Add Integration
				</n-button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount } from "vue"
import { useMessage, NSpin, NEmpty, NButton, NScrollbar, NSteps, NStep, type StepsProps } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import IntegrationsList from "@/components/integrations/IntegrationsList.vue"
import type { CustomerIntegration } from "@/types/integrations"

const { customerCode } = defineProps<{
	customerCode: string
}>()

const emit = defineEmits<{
	(e: "close"): void
}>()

const AddIcon = "carbon:add-alt"
const SkipIcon = "carbon:subtract"
const ArrowRightIcon = "carbon:arrow-right"
const ArrowLeftIcon = "carbon:arrow-left"

const message = useMessage()
const current = ref<number>(1)
const currentStatus = ref<StepsProps["status"]>("process")
const slideFormDirection = ref<"right" | "left">("right")
const showForm = ref(false)
const isWazuhStepEnabled = ref(false)
const isPrevStepEnabled = ref(false)
const isNextStepEnabled = ref(true)
const isSubmitEnabled = ref(true)
const loading = ref(false)
const loadingIntegrations = ref(false)
const integrationsList = ref<CustomerIntegration[]>([])

function getCustomerIntegrations() {
	loadingIntegrations.value = true

	Api.integrations
		.getCustomerIntegrations(customerCode)
		.then(res => {
			if (res.data.success) {
				integrationsList.value = res.data?.available_integrations || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingIntegrations.value = false
		})
}

function validate() {}

function next() {
	currentStatus.value = "process"
	slideFormDirection.value = "right"
	current.value++
}

function prev() {
	currentStatus.value = "process"
	slideFormDirection.value = "left"
	current.value--
}
</script>

<style lang="scss" scoped>
.customer-integration-form {
	height: 450px;
	overflow: hidden;

	.slide-form-right-enter-active,
	.slide-form-right-leave-active,
	.slide-form-left-enter-active,
	.slide-form-left-leave-active {
		transition: all 0.2s ease-out;
		position: absolute;
		width: 100%;
	}

	.slide-form-left-enter-from {
		transform: translateX(-100%);
	}

	.slide-form-left-leave-to {
		transform: translateX(100%);
	}

	.slide-form-right-enter-from {
		transform: translateX(100%);
	}

	.slide-form-right-leave-to {
		transform: translateX(-100%);
	}
}
</style>
