<template>
	<n-spin :show="loading" class="active-response-wizard">
		<div class="wrapper flex flex-col">
			<div class="grow flex flex-col">
				<n-scrollbar x-scrollable trigger="none">
					<div class="p-7 pt-4">
						<n-steps :current="current" size="small" :status="currentStatus">
							<n-step title="Operative System" />
							<n-step title="Active Response" />
							<n-step title="Submission" />
						</n-steps>
					</div>
				</n-scrollbar>

				<div class="mt-4 grow flex flex-col">
					<Transition :name="`slide-form-${slideFormDirection}`">
						<div v-if="current === 1" class="px-7 flex flex-col gap-2">
							<div class="os-button" @click="setOs('linux')">
								<Icon :size="18" :name="iconFromOs('linux')"></Icon>
								<span>LINUX</span>
							</div>
							<div class="os-button" @click="setOs('windows')">
								<Icon :size="18" :name="iconFromOs('windows')"></Icon>
								<span>WINDOWS</span>
							</div>
							<div class="os-button" @click="setOs('macos')">
								<Icon :size="18" :name="iconFromOs('macos')"></Icon>
								<span>MACOS</span>
							</div>
						</div>

						<div v-else-if="current === 2" class="px-7">
							<n-spin :show="loadingActiveResponse">
								<div class="list">
									<template v-if="activeResponseFiltered.length">
										<ActiveResponseItem
											v-for="activeResponse of activeResponseFiltered"
											:key="activeResponse.name"
											:activeResponse="activeResponse"
											embedded
											hide-actions
											class="mb-2 cursor-pointer"
											@click="setActiveResponse(activeResponse)"
										/>
									</template>
									<template v-else>
										<n-empty
											description="No items found"
											class="justify-center h-48"
											v-if="!loadingActiveResponse"
										/>
									</template>
								</div>
							</n-spin>
						</div>
						<div v-else-if="current === 3" class="px-7 grow flex flex-col pb-7" style="min-height: 401px">
							<ActiveResponseInvokeForm
								v-if="selectedActiveResponse"
								:activeResponse="selectedActiveResponse"
								@mounted="activeResponseInvokeFormCTX = $event"
								@submitted="reset()"
								@startLoading="loadingActiveResponseInvoke = true"
								@stopLoading="loadingActiveResponseInvoke = false"
							>
								<template #additionalActions>
									<n-button @click="prev()" :disabled="loadingActiveResponseInvoke">
										<template #icon>
											<Icon :name="ArrowLeftIcon"></Icon>
										</template>
										Prev
									</n-button>
								</template>
							</ActiveResponseInvokeForm>
						</div>
					</Transition>
				</div>
			</div>

			<div class="flex justify-between gap-4 p-7 pt-4" v-if="current !== 3">
				<div class="flex gap-4">
					<slot name="additionalActions"></slot>
				</div>
				<div class="flex gap-4">
					<n-button @click="prev()" v-if="isPrevStepEnabled">
						<template #icon>
							<Icon :name="ArrowLeftIcon"></Icon>
						</template>
						Prev
					</n-button>
				</div>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue"
import { NSteps, NStep, useMessage, NScrollbar, NButton, NEmpty, NSpin, type StepsProps } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import { onBeforeMount } from "vue"
import type { SupportedActiveResponse } from "@/types/activeResponse.d"
import ActiveResponseItem from "./ActiveResponseItem.vue"
import ActiveResponseInvokeForm from "./ActiveResponseInvokeForm.vue"
import { iconFromOs } from "@/utils"
import type { OsTypesLower } from "@/types/common"

const emit = defineEmits<{
	(e: "update:loading", value: boolean): void
	(
		e: "mounted",
		value: {
			reset: () => void
		}
	): void
}>()

const ArrowLeftIcon = "carbon:arrow-left"

const loadingActiveResponse = ref(false)
const loadingActiveResponseInvoke = ref(false)
const loading = computed(() => loadingActiveResponseInvoke.value)
const slideFormDirection = ref<"right" | "left">("right")
const activeResponseList = ref<SupportedActiveResponse[]>([])
const message = useMessage()
const current = ref<number>(1)
const currentStatus = ref<StepsProps["status"]>("process")
const selectedOS = ref<OsTypesLower | null>(null)
const selectedActiveResponse = ref<SupportedActiveResponse | null>(null)
const activeResponseInvokeFormCTX = ref<{ reset: () => void } | null>(null)

watch(loading, val => {
	emit("update:loading", val)
})

const activeResponseFiltered = computed(() => {
	if (selectedOS.value === null) {
		return activeResponseList.value
	}
	return activeResponseList.value.filter(o => o.name.toLowerCase().indexOf(selectedOS.value || "") === 0)
})
const isPrevStepEnabled = computed(() => current.value > 1)

function next() {
	currentStatus.value = "process"
	slideFormDirection.value = "right"
	current.value++
}

function prev() {
	currentStatus.value = "process"
	slideFormDirection.value = "left"
	current.value--
	activeResponseInvokeFormCTX.value?.reset()
}

function reset() {
	if (!loadingActiveResponseInvoke.value) {
		currentStatus.value = "process"
		slideFormDirection.value = "right"
		current.value = 1
		selectedOS.value = null
		selectedActiveResponse.value = null
		activeResponseInvokeFormCTX.value?.reset()
	}
}

function getActiveResponseList() {
	loadingActiveResponse.value = true

	Api.activeResponse
		.getSupported()
		.then(res => {
			if (res.data.success) {
				activeResponseList.value = res.data?.supported_active_responses || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingActiveResponse.value = false
		})
}

function setOs(os: OsTypesLower) {
	selectedOS.value = os
	next()
}

function setActiveResponse(activeResponse: SupportedActiveResponse) {
	selectedActiveResponse.value = activeResponse
	next()
}

onBeforeMount(() => {
	getActiveResponseList()
})

onMounted(() => {
	emit("mounted", {
		reset
	})
})
</script>

<style lang="scss" scoped>
.active-response-wizard {
	.wrapper {
		min-height: 480px;
	}

	.os-button {
		border-radius: var(--border-radius);
		background-color: var(--bg-secondary-color);
		border: var(--border-small-050);
		transition: all 0.2s var(--bezier-ease);
		cursor: pointer;
		line-height: 1;
		@apply p-4 flex gap-3 items-center;

		&:hover {
			box-shadow: 0px 0px 0px 1px inset var(--primary-color);
		}
	}

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
