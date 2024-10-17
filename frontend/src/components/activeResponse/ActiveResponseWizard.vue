<template>
	<n-spin :show="loading" class="active-response-wizard">
		<div class="wrapper flex flex-col">
			<div class="flex grow flex-col">
				<n-scrollbar x-scrollable trigger="none">
					<div class="p-7 pt-4">
						<n-steps :current="current" size="small" :status="currentStatus">
							<n-step title="Operative System" />
							<n-step title="Active Response" />
							<n-step title="Submission" />
						</n-steps>
					</div>
				</n-scrollbar>

				<div class="mt-4 flex grow flex-col">
					<Transition :name="`slide-form-${slideFormDirection}`">
						<div v-if="current === 1" class="flex flex-col gap-2 px-7">
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
											:active-response="activeResponse"
											embedded
											hide-actions
											class="mb-2 cursor-pointer"
											@click="setActiveResponse(activeResponse)"
										/>
									</template>
									<template v-else>
										<n-empty
											v-if="!loadingActiveResponse"
											description="No items found"
											class="h-48 justify-center"
										/>
									</template>
								</div>
							</n-spin>
						</div>
						<div v-else-if="current === 3" class="flex grow flex-col px-7 pb-7" style="min-height: 401px">
							<ActiveResponseInvokeForm
								v-if="selectedActiveResponse"
								:active-response="selectedActiveResponse"
								@mounted="activeResponseInvokeFormCTX = $event"
								@submitted="reset()"
								@start-loading="loadingActiveResponseInvoke = true"
								@stop-loading="loadingActiveResponseInvoke = false"
							>
								<template #additionalActions>
									<n-button :disabled="loadingActiveResponseInvoke" @click="prev()">
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

			<div v-if="current !== 3" class="flex justify-between gap-4 p-7 pt-4">
				<div class="flex gap-4">
					<slot name="additionalActions"></slot>
				</div>
				<div class="flex gap-4">
					<n-button v-if="isPrevStepEnabled" @click="prev()">
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
import type { SupportedActiveResponse } from "@/types/activeResponse.d"
import type { OsTypesLower } from "@/types/common.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { iconFromOs } from "@/utils"
import { NButton, NEmpty, NScrollbar, NSpin, NStep, NSteps, type StepsProps, useMessage } from "naive-ui"
import { computed, onBeforeMount, onMounted, ref, watch } from "vue"
import ActiveResponseInvokeForm from "./ActiveResponseInvokeForm.vue"
import ActiveResponseItem from "./ActiveResponseItem.vue"

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
		@apply flex items-center gap-3 p-4;

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
