<template>
	<div class="simulator-windows-attack-wizard min-h-120 flex flex-col gap-4 overflow-hidden">
		<div>
			<n-scrollbar x-scrollable trigger="none">
				<div class="px-7 pb-2 pt-4">
					<n-steps :current="current" size="small" :status="currentStatus">
						<n-step title="Attack" />
						<n-step title="Endpoint agent" />
						<n-step title="Simulate" />
					</n-steps>
				</div>
			</n-scrollbar>
		</div>

		<div class="flex grow flex-col overflow-hidden">
			<Transition :name="`slide-form-${slideFormDirection}`">
				<div v-if="current === 1" class="grow overflow-hidden">
					<n-scrollbar style="max-height: 355px" trigger="none">
						<ParametersList v-model:selected="selectedAttack" :technique-id class="px-7" />
					</n-scrollbar>
				</div>
				<div v-if="current === 2" class="grow overflow-hidden">
					<n-scrollbar style="max-height: 355px" trigger="none">
						<ParametersList v-model:selected="selectedAttack" :technique-id class="px-7" />
					</n-scrollbar>
				</div>
				<div v-else class="auth-key-form flex flex-wrap gap-3 px-7">recap...</div>
			</Transition>
		</div>

		<div class="flex justify-between gap-4 px-7 pb-4">
			<n-button v-if="isPrevStepEnabled" @click="prev()">
				<template #icon>
					<Icon :name="ArrowLeftIcon"></Icon>
				</template>
				Prev
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
</template>

<script setup lang="ts">
import type { StepsProps } from "naive-ui"
import type { CollectRequest } from "@/api/endpoints/artifacts"
import type { Agent } from "@/types/agents.d"
import type { MatchingParameter } from "@/types/artifacts.d"
import { NButton, NScrollbar, NStep, NSteps, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import ParametersList from "./ParametersList.vue"

const { techniqueId } = defineProps<{
	techniqueId: string
}>()

const emit = defineEmits<{
	(e: "update:loading", value: boolean): void
	(e: "close"): void
	(e: "submitted"): void
}>()

const ArrowLeftIcon = "carbon:arrow-left"

const message = useMessage()
const current = ref<number>(1)
const currentStatus = ref<StepsProps["status"]>("process")
const slideFormDirection = ref<"right" | "left">("right")

const selectedAttack = ref<MatchingParameter | null>(null)
const selectedAgent = ref<Agent | null>(null)

watch(selectedAttack, val => {
	if (val) {
		next()
	}
})

const isPrevStepEnabled = computed(() => current.value > 1)
const isSubmitEnabled = computed(() => current.value === 2)
const isSubmitValid = computed(() => {
	if (!selectedAttack.value) {
		return false
	}

	if (!selectedAgent.value) {
		return false
	}

	return true
})

const loading = ref(false)

function submit() {
	if (selectedAttack.value && selectedAgent.value) {
		currentStatus.value = "finish"
		loading.value = true

		const payload: CollectRequest = {
			hostname: selectedAgent.value.hostname,
			artifact_name: "Windows.AttackSimulation.AtomicRedTeam",
			parameters: {
				env: [
					{
						key: "InstallART",
						value: "N"
					},
					{
						key: selectedAttack.value.name,
						value: "Y"
					}
				]
			}
		}

		Api.artifacts
			.collect(payload)
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

function reset() {
	currentStatus.value = "process"
	slideFormDirection.value = "right"
	current.value = 1

	selectedAttack.value = null
	selectedAgent.value = null
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
.simulator-windows-attack-wizard {
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
