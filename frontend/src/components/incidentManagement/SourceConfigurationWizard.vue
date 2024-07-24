<template>
	<n-spin :show="loading" class="source-configuration-wizard">
		<div class="wrapper flex flex-col">
			<div class="grow flex flex-col">
				<n-scrollbar x-scrollable trigger="none">
					<div class="p-7 pt-4">
						<n-steps :current="current" size="small" :status="currentStatus">
							<n-step title="Source" />
							<n-step title="Configuration" />
						</n-steps>
					</div>
				</n-scrollbar>

				<div class="mt-4 grow flex flex-col">
					<Transition :name="`slide-form-${slideFormDirection}`">
						<div v-if="current === 1" class="px-7 flex flex-col gap-4">
							<n-select
								v-model:value="selectedIndex"
								placeholder="Indices list"
								clearable
								filterable
								to="body"
								:loading="loadingIndices"
								:options="indexNamesOptions"
								@update:value="setSourceConfiguration(selectedIndex)"
							></n-select>

							<div class="flex gap-4 justify-end">
								<n-button
									@click="next()"
									v-if="isNextStepEnabled"
									icon-placement="right"
									:disabled="!selectedIndex"
								>
									<template #icon>
										<Icon :name="ArrowRightIcon"></Icon>
									</template>
									Next
								</n-button>
							</div>
						</div>

						<div v-else-if="current === 2" class="px-7 grow flex flex-col pb-7" style="min-height: 401px">
							<SourceConfigurationForm
								v-if="sourceConfigurationPayload"
								:sourceConfigurationPayload
								show-source-field
								disable-source-field
								show-index-name-field
								disable-index-name-field
								@mounted="formCTX = $event"
								@submitted="createSourceConfiguration($event)"
							>
								<template #additionalActions>
									<n-button @click="prev()" :disabled="submitting" v-if="isPrevStepEnabled">
										<template #icon>
											<Icon :name="ArrowLeftIcon"></Icon>
										</template>
										Prev
									</n-button>
								</template>
							</SourceConfigurationForm>
						</div>
					</Transition>
				</div>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue"
import { NSteps, NStep, useMessage, NScrollbar, NButton, NSpin, NSelect, type StepsProps } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import { onBeforeMount } from "vue"
import SourceConfigurationForm from "./SourceConfigurationForm.vue"
import type { ApiError } from "@/types/common.d"
import type { SourceConfiguration } from "@/types/incidentManagement.d"
import type { SourceConfigurationPayload } from "@/api/endpoints/incidentManagement"

const emit = defineEmits<{
	(e: "update:loading", value: boolean): void
	(e: "submitted"): void
	(
		e: "mounted",
		value: {
			reset: () => void
		}
	): void
}>()

const ArrowLeftIcon = "carbon:arrow-left"
const ArrowRightIcon = "carbon:arrow-right"
const loadingIndices = ref(false)
const submitting = ref(false)
const loading = computed(() => submitting.value)
const slideFormDirection = ref<"right" | "left">("right")
const message = useMessage()
const current = ref<number>(1)
const currentStatus = ref<StepsProps["status"]>("process")
const formCTX = ref<{ reset: () => void; toggleSubmittingFlag: () => boolean } | null>(null)
const selectedIndex = ref<string | null>(null)
const sourceConfigurationPayload = ref<SourceConfigurationPayload | null>(null)
const indexNamesOptions = ref<{ label: string; value: string }[]>([])

watch(loading, val => {
	emit("update:loading", val)
})

const isPrevStepEnabled = computed(() => current.value > 1)
const isNextStepEnabled = computed(() => current.value < 2)

function next() {
	currentStatus.value = "process"
	slideFormDirection.value = "right"
	current.value++
}

function prev() {
	currentStatus.value = "process"
	slideFormDirection.value = "left"
	current.value--
	formCTX.value?.reset()
}

function reset(force?: boolean) {
	if (!submitting.value || force) {
		currentStatus.value = "process"
		slideFormDirection.value = "right"
		current.value = 1
		selectedIndex.value = null
		sourceConfigurationPayload.value = null
		formCTX.value?.reset()
	}
}

function setSourceConfiguration(indexName: string | null) {
	if (indexName) {
		sourceConfigurationPayload.value = {
			field_names: [],
			asset_name: "",
			timefield_name: "",
			alert_title_name: "",
			source: "",
			index_name: indexName
		}
		next()
	}
}

function getIndices() {
	loadingIndices.value = true

	Api.graylog
		.getIndices()
		.then(res => {
			if (res.data.success) {
				indexNamesOptions.value = (res.data?.indices || []).map(o => ({
					label: o.index_name,
					value: o.index_name
				}))
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingIndices.value = false
		})
}

function createSourceConfiguration(payload: SourceConfiguration) {
	submitting.value = formCTX.value?.toggleSubmittingFlag() || true

	Api.incidentManagement
		.setSourceConfiguration(payload)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || `Source Configuration sent successfully`)
				reset(true)
				emit("submitted")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch((err: ApiError) => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			submitting.value = formCTX.value?.toggleSubmittingFlag() || false
		})
}

onBeforeMount(() => {
	getIndices()
})

onMounted(() => {
	emit("mounted", {
		reset
	})
})
</script>

<style lang="scss" scoped>
.source-configuration-wizard {
	.wrapper {
		min-height: 180px;
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
