<template>
	<n-spin :show="loading" class="source-configuration-wizard">
		<div class="flex min-h-48 flex-col">
			<div class="flex grow flex-col">
				<n-scrollbar x-scrollable trigger="none">
					<div class="p-7 pt-4">
						<n-steps :current="current" size="small" :status="currentStatus">
							<n-step title="Source" />
							<n-step title="Configuration" />
						</n-steps>
					</div>
				</n-scrollbar>

				<div class="mt-4 flex grow flex-col">
					<Transition :name="`slide-form-${slideFormDirection}`">
						<div v-if="current === 1" class="flex flex-col gap-4 px-7">
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

							<div class="flex justify-end gap-4">
								<n-button @click="overrideMode()">Manual override</n-button>
								<n-button
									v-if="isNextStepEnabled"
									icon-placement="right"
									:disabled="!selectedIndex"
									@click="standardMode()"
								>
									<template #icon>
										<Icon :name="ArrowRightIcon"></Icon>
									</template>
									Next
								</n-button>
							</div>
						</div>

						<div v-else-if="current === 2" class="flex min-h-[401px] grow flex-col px-7 pb-7">
							<SourceConfigurationForm
								v-if="sourceConfigurationModel"
								:source-configuration-model
								show-source-field
								disable-source-field
								:show-index-name-field
								:arbitrary-source-field
								disable-index-name-field
								:disabled-sources
								@mounted="formCTX = $event"
								@submitted="createSourceConfiguration($event)"
							>
								<template #additionalActions>
									<n-button v-if="isPrevStepEnabled" :disabled="submitting" @click="prev()">
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
import type { ApiError } from "@/types/common.d"
import type { SourceConfiguration, SourceConfigurationModel, SourceName } from "@/types/incidentManagement/sources.d"
import type { StepsProps } from "naive-ui"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { NButton, NScrollbar, NSelect, NSpin, NStep, NSteps, useMessage } from "naive-ui"
import { computed, onBeforeMount, onMounted, ref, toRefs, watch } from "vue"
import SourceConfigurationForm from "./SourceConfigurationForm.vue"

const props = defineProps<{ disabledSources?: SourceName[] }>()

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

const { disabledSources } = toRefs(props)

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
const sourceConfigurationModel = ref<SourceConfigurationModel | null>(null)
const indexNamesOptions = ref<{ label: string; value: string }[]>([])

watch(loading, val => {
	emit("update:loading", val)
})

const isPrevStepEnabled = computed(() => current.value > 1)
const isNextStepEnabled = computed(() => current.value < 2)
const showIndexNameField = ref(true)
const arbitrarySourceField = ref(false)

function overrideMode() {
	showIndexNameField.value = false
	arbitrarySourceField.value = true
	setSourceConfiguration(null)
	next()
}

function standardMode() {
	showIndexNameField.value = true
	arbitrarySourceField.value = false
	next()
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
	formCTX.value?.reset()
}

function reset(force?: boolean) {
	if (!submitting.value || force) {
		currentStatus.value = "process"
		slideFormDirection.value = "right"
		current.value = 1
		selectedIndex.value = null
		sourceConfigurationModel.value = null
		formCTX.value?.reset()
	}
}

function setSourceConfiguration(indexName: string | null) {
	if (indexName) {
		sourceConfigurationModel.value = {
			field_names: [],
			ioc_field_names: [],
			asset_name: null,
			timefield_name: null,
			alert_title_name: null,
			source: "",
			index_name: indexName
		}
		next()
	} else {
		sourceConfigurationModel.value = {
			field_names: [],
			ioc_field_names: [],
			asset_name: null,
			timefield_name: null,
			alert_title_name: null,
			source: "",
			index_name: ""
		}
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
		.createSourceConfiguration(payload)
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
