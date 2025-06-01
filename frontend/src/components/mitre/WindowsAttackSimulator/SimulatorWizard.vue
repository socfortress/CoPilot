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
					<n-scrollbar ref="parametersScroll" style="max-height: 350px" trigger="none">
						<ParametersList
							v-model:selected="selectedAttack"
							:technique-id
							class="px-7"
							:parameters-list
							@loaded="parametersList = $event"
						/>
					</n-scrollbar>
				</div>
				<div v-else-if="current === 2" class="grow overflow-hidden">
					<n-scrollbar ref="agentsScroll" style="max-height: 350px" trigger="none">
						<AgentsList
							v-model:selected="selectedAgent"
							class="px-7"
							:agents-list
							:filter="agentsListFilter"
							@loaded="agentsList = $event"
						/>
					</n-scrollbar>
				</div>
				<div v-else class="flex flex-col gap-6 px-7">
					<CardEntity size="small" embedded>
						<template #header>selected</template>
						<template #footer>
							<div class="flex flex-col gap-2">
								<CardEntity v-if="selectedAttack" embedded size="small">
									<template #header>
										{{ selectedAttack.name }}
									</template>
									<template #default>
										{{ selectedAttack.description }}
									</template>
								</CardEntity>
								<CardEntity v-if="selectedAgent" embedded size="small">
									<template #headerMain>
										{{ selectedAgent.hostname }}
									</template>
									<template #headerExtra>
										<code
											class="text-primary cursor-pointer"
											@click.stop="gotoAgent(selectedAgent.agent_id)"
										>
											{{ selectedAgent.agent_id }}
											<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
										</code>
									</template>
									<template #default>
										{{ selectedAgent.ip_address }}
										<code>{{ selectedAgent.label }}</code>
									</template>
									<template #footer>
										{{ selectedAgent.os }}
									</template>
								</CardEntity>
							</div>
						</template>
					</CardEntity>

					<div v-if="collectResponse" class="flex flex-col gap-2">
						<div v-if="collectTime" class="text-xs">
							<span class="text-sm">last simulation:</span>
							<code>{{ formatDate(collectTime, dFormats.datetimesec) }}</code>
						</div>
						<CardEntity v-for="report of collectResponse" :key="`${report.GUID}`" size="small">
							<template #default>
								<table>
									<tbody class="text-xs">
										<tr v-for="(value, key) in report" :key="`${key}`">
											<td class="text-secondary whitespace-nowrap p-1 pr-4">{{ key }}</td>
											<td class="p-1">{{ value }}</td>
										</tr>
									</tbody>
								</table>
							</template>
						</CardEntity>
					</div>
					<template v-else>
						<div v-if="!loading" class="p-6 text-center">
							Run “
							<strong>Simulate attack</strong>
							” to view the report here.
						</div>
						<div v-else class="flex flex-col gap-2">
							<n-skeleton height="20px" width="50%" :sharp="false" />
							<n-skeleton height="100px" width="100%" :sharp="false" />
						</div>
					</template>
				</div>
			</Transition>
		</div>

		<div class="flex justify-between gap-4 px-7 pb-4">
			<div class="flex items-center gap-4">
				<n-button v-if="isPrevStepEnabled" :disabled="loading" @click="prev()">
					<template #icon>
						<Icon :name="ArrowLeftIcon"></Icon>
					</template>
					Prev
				</n-button>
				<n-button v-if="isNextStepEnabled" icon-placement="right" :disabled="loading" @click="next()">
					<template #icon>
						<Icon :name="ArrowRightIcon"></Icon>
					</template>
					Next
				</n-button>
			</div>
			<n-button v-if="isSubmitEnabled" type="primary" :disabled="!isSubmitValid" :loading @click="submit()">
				<template #icon>
					<Icon :name="AttackIcon"></Icon>
				</template>
				Simulate attack
			</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ScrollbarInst, StepsProps } from "naive-ui"
import type { CollectRequest } from "@/api/endpoints/artifacts"
import type { Agent } from "@/types/agents.d"
import type { MatchingParameter } from "@/types/artifacts.d"
import { NButton, NScrollbar, NSkeleton, NStep, NSteps, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import AgentsList from "./AgentsList.vue"
import ParametersList from "./ParametersList.vue"

export interface Report {
	"Execution Time (UTC)": Date
	"Execution Time (Local)": Date
	Technique: string
	"Test Number": number
	"Test Name": string
	Hostname: string
	Username: string
	GUID: string
}

const { techniqueId } = defineProps<{
	techniqueId: string
}>()

const emit = defineEmits<{
	(e: "update:loading", value: boolean): void
	(e: "close"): void
	(e: "submitted"): void
}>()

const ArrowRightIcon = "carbon:arrow-right"
const ArrowLeftIcon = "carbon:arrow-left"
const AttackIcon = "mdi:target"
const LinkIcon = "carbon:launch"

const { gotoAgent } = useGoto()
const dFormats = useSettingsStore().dateFormat
const message = useMessage()
const current = ref<number>(1)
const currentStatus = ref<StepsProps["status"]>("process")
const slideFormDirection = ref<"right" | "left">("right")

const parametersList = ref<MatchingParameter[] | null>(null)
const agentsList = ref<Agent[] | null>(null)
const selectedAttack = ref<MatchingParameter | null>(null)
const selectedAgent = ref<Agent | null>(null)
const loading = ref(false)
const collectResponse = ref<Report[] | null>(null)
const collectTime = ref<Date | null>(null)
const parametersScroll = ref<ScrollbarInst | null>(null)
const agentsScroll = ref<ScrollbarInst | null>(null)

const isNextStepEnabled = computed(
	() => (current.value === 1 && selectedAttack.value) || (current.value === 2 && selectedAgent.value)
)
const isPrevStepEnabled = computed(() => current.value > 1)
const isSubmitEnabled = computed(() => current.value === 3)
const isSubmitValid = computed(() => {
	if (!selectedAttack.value) {
		return false
	}

	if (!selectedAgent.value) {
		return false
	}

	return true
})

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
					collectResponse.value = (res.data.results as unknown as Report[]) || []
					collectTime.value = new Date()
					message.success(res.data?.message || "Successfully executed query.")
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				// MOCK
				/*
				const res = {
					message: "Successfully executed query",
					success: true,
					results: [
						{
							"Execution Time (UTC)": "2025-05-31T20:43:02Z",
							"Execution Time (Local)": "2025-05-31T13:43:02Z",
							Technique:
								"[T1003.001](https://github.com/redcanaryco/atomic-red-team/blob/master/atomics/T1003.001/T1003.001.md)",
							"Test Number": 10,
							"Test Name": "Powershell Mimikatz",
							Hostname: "WIN-HFOU106TD7K",
							Username: "nt authority\\system",
							GUID: "66fb0bc1-3c3f-47e9-a298-550ecfefacbc"
						}
					]
				}

				emit("submitted")
				collectResponse.value = (res.results as unknown as Report[]) || []
				collectTime.value = new Date()
				message.success(res?.message || "Successfully executed query.")

				throw err
				*/
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				loading.value = false
			})
	}
}

function _reset() {
	currentStatus.value = "process"
	slideFormDirection.value = "right"
	current.value = 1

	selectedAttack.value = null
	selectedAgent.value = null
	collectResponse.value = null
	collectTime.value = null
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

function agentsListFilter(agent: Agent) {
	return agent.os.toLowerCase().includes("window")
}

function scrollInView(scrollContainer: ScrollbarInst) {
	// @ts-expect-error $el property not mapped
	const wrap = (scrollContainer.$el.nextSibling || scrollContainer.$el.nextElementSibling) as HTMLElement

	const element = wrap.querySelector(".highlighted") as HTMLElement

	if (element) {
		const middle = element.offsetTop - wrap.offsetHeight / 2 + element.offsetHeight / 2

		scrollContainer.scrollTo({ top: middle, behavior: "smooth" })
	}
}

watch(selectedAttack, val => {
	if (val) {
		next()
	}
})

watch(selectedAgent, val => {
	if (val) {
		next()
	}
})

watch([current, parametersList, agentsList], () => {
	if (current.value === 1 && parametersList.value?.length && selectedAttack.value) {
		setTimeout(() => {
			if (parametersScroll.value) {
				scrollInView(parametersScroll.value)
			}
		}, 200)
	}
	if (current.value === 2 && agentsList.value?.length && selectedAgent.value) {
		setTimeout(() => {
			if (agentsScroll.value) {
				scrollInView(agentsScroll.value)
			}
		}, 200)
	}
})
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
