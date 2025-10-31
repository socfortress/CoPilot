<template>
	<div class="customer-integration-form flex min-h-120 flex-col gap-4 overflow-hidden">
		<div>
			<n-scrollbar x-scrollable trigger="none">
				<div class="px-7 pt-4 pb-2">
					<n-steps :current="current" size="small" :status="currentStatus">
						<n-step title="Choose Integration" />
						<n-step title="Set Auth Keys">
							<template #icon>
								<Icon v-if="!isAuthKeysStepEnabled" :name="SkipIcon"></Icon>
							</template>
						</n-step>
					</n-steps>
				</div>
			</n-scrollbar>
		</div>

		<div class="flex grow flex-col overflow-hidden">
			<Transition :name="`slide-form-${slideFormDirection}`">
				<div v-if="current === 1" class="available-list grow overflow-hidden">
					<n-scrollbar style="max-height: 355px" trigger="none">
						<IntegrationsList
							v-model:selected="selectedIntegration"
							embedded
							hide-totals
							selectable
							:disabled-ids-list="disabledIdsList"
							class="px-7"
						/>
					</n-scrollbar>
				</div>
				<div v-else class="auth-key-form flex flex-wrap gap-3 px-7">
					<template v-for="ak of authKeysForm" :key="ak.key">
						<n-form-item v-if="ak.type === 'string'" :label="ak.key" required class="grow">
							<n-input v-model:value="ak.value" :placeholder="`Input ${ak.key}...`" clearable />
						</n-form-item>
						<n-form-item v-if="ak.type === 'selectType'" :label="ak.key" required class="grow">
							<n-select
								v-model:value="ak.value"
								:options="apiTypeOptions"
								:placeholder="`Input ${ak.key}...`"
								class="min-w-36"
								clearable
							/>
						</n-form-item>
					</template>
				</div>
			</Transition>
		</div>

		<div class="flex justify-between gap-4 px-7 pb-4">
			<div class="flex gap-4">
				<n-button @click="close()">Close</n-button>
			</div>
			<div class="flex gap-4">
				<n-button v-if="isPrevStepEnabled" @click="prev()">
					<template #icon>
						<Icon :name="ArrowLeftIcon"></Icon>
					</template>
					Prev
				</n-button>
				<n-button v-if="isNextStepShown" :disabled="!isNextStepEnabled" icon-placement="right" @click="next()">
					<template #icon>
						<Icon :name="ArrowRightIcon"></Icon>
					</template>
					Next
				</n-button>
				<n-button
					v-if="isSubmitEnabled"
					type="primary"
					:disabled="!isSubmitValid"
					:loading="loading"
					@click="submit()"
				>
					Submit
				</n-button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { StepsProps } from "naive-ui"
import type { NewIntegration } from "@/api/endpoints/integrations"
import type { ServiceItemData } from "@/components/services/types"
import { NButton, NFormItem, NInput, NScrollbar, NSelect, NStep, NSteps, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import IntegrationsList from "@/components/integrations/IntegrationsList.vue"

interface AuthKeysInput {
	key: string
	value: string
	type: "selectType" | "string"
}

const { customerCode, customerName, disabledIdsList } = defineProps<{
	customerCode: string
	customerName: string
	disabledIdsList?: (string | number)[]
}>()

const emit = defineEmits<{
	(e: "update:loading", value: boolean): void
	(e: "close"): void
	(e: "submitted"): void
}>()

const SkipIcon = "carbon:subtract"
const ArrowRightIcon = "carbon:arrow-right"
const ArrowLeftIcon = "carbon:arrow-left"

const message = useMessage()
const current = ref<number>(1)
const currentStatus = ref<StepsProps["status"]>("process")
const slideFormDirection = ref<"right" | "left">("right")

const selectedIntegration = ref<ServiceItemData | null>(null)
const authKeysForm = ref<AuthKeysInput[]>([])
const apiTypeOptions = [
	{ label: "Commercial", value: "commercial" },
	{ label: "GCC", value: "gcc" },
	{ label: "GCC-High", value: "gcc-high" }
]

watch(selectedIntegration, val => {
	authKeysForm.value = []

	if (val !== null) {
		for (const ak of val.keys) {
			authKeysForm.value.push({
				key: ak.auth_key_name,
				value: ak.auth_key_name === "API_TYPE" ? apiTypeOptions[0].value : "",
				type: ak.auth_key_name === "API_TYPE" ? "selectType" : "string"
			})
		}
	}
})

const isAuthKeysStepEnabled = computed(() => selectedIntegration.value !== null)
const isNextStepShown = computed(() => current.value === 1)
const isNextStepEnabled = computed(() => isNextStepShown.value && isAuthKeysStepEnabled.value)
const isPrevStepEnabled = computed(() => current.value > 1)
const isSubmitEnabled = computed(() => current.value === 2)
const isSubmitValid = computed(() => {
	if (!isSubmitEnabled.value) {
		return false
	}

	const keys = authKeysForm.value.length
	const valid = authKeysForm.value.filter(o => !!o.value).length

	return valid === keys
})

const loading = ref(false)

function submit() {
	if (selectedIntegration.value) {
		currentStatus.value = "finish"
		loading.value = true

		const payload: NewIntegration = {
			customer_code: customerCode,
			customer_name: customerName,
			integration_name: selectedIntegration.value.name,
			integration_auth_keys: authKeysForm.value.map(o => ({
				auth_key_name: o.key,
				auth_value: o.value
			}))
		}

		Api.integrations
			.createIntegration(payload)
			.then(res => {
				if (res.data.success) {
					emit("submitted")
					reset()
					message.success(res.data?.message || "Customer integration successfully created.")
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
}

function close() {
	reset()
	emit("close")
}

function reset() {
	currentStatus.value = "process"
	slideFormDirection.value = "right"
	current.value = 1

	selectedIntegration.value = null
	authKeysForm.value = []
}

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
