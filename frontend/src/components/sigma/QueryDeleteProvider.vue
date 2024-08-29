<template>
	<n-popover trigger="click" to="body" content-class="px-0" v-model:show="show">
		<template #trigger>
			<slot :loading />
		</template>

		<div class="py-1 flex gap-2">
			<n-input-group>
				<n-select
					v-model:value="model.unit"
					:options="unitOptions"
					placeholder="Time unit"
					:disabled="loading"
					class="!w-28"
				/>
				<n-input-number
					v-model:value="model.time"
					:min="1"
					clearable
					placeholder="Time"
					class="!w-32"
					:disabled="loading"
				/>
			</n-input-group>

			<n-button :disabled="!dirty || !isValid" :loading @click="updateTimeInterval()" type="primary">
				Save
			</n-button>
		</div>
	</n-popover>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, ref, toRefs, watch } from "vue"
import { NSelect, NInputGroup, NButton, NInputNumber, NPopover, useMessage } from "naive-ui"
import Api from "@/api"
import type { SigmaQuery, SigmaTimeInterval, SigmaTimeIntervalUnit } from "@/types/sigma.d"

const props = defineProps<{
	query: SigmaQuery
}>()
const { query } = toRefs(props)

const emit = defineEmits<{
	(e: "deleted", value: SigmaQuery): void
}>()

const show = ref(false)
const loading = ref(false)
const message = useMessage()
const model = ref<{ time: number; unit: SigmaTimeIntervalUnit }>({ time: 1, unit: "m" })
const unitOptions = [
	{ label: "Minutes", value: "m" },
	{ label: "Hours", value: "h" },
	{ label: "Days", value: "d" }
]
const timeUnit = ref<SigmaTimeIntervalUnit>("m")
const timeValue = ref<number>(1)

const timeInterval = computed<SigmaTimeInterval>(() => `${timeValue.value}${timeUnit.value}`)
const modelTimeInterval = computed<SigmaTimeInterval>(() => `${model.value.time}${model.value.unit}`)

const dirty = computed(() => timeInterval.value !== modelTimeInterval.value)
const isValid = computed(() => model.value.time && model.value.unit)

watch(show, val => {
	if (val && !loading.value) {
		setModel()
	}
})

function setModel() {
	if (query.value.time_interval) {
		timeUnit.value = (
			query.value.time_interval.match(/[a-z]/i)?.[0] || "m"
		).toLocaleLowerCase() as SigmaTimeIntervalUnit
		timeValue.value = parseInt(query.value.time_interval.match(/\d+/)?.[0] || "1")

		model.value.unit = timeUnit.value
		model.value.time = timeValue.value
	}
}

function updateTimeInterval() {
	if (query.value.rule_name && modelTimeInterval.value) {
		loading.value = true

		Api.sigma
			.setQueryTimeInterval(query.value.rule_name, modelTimeInterval.value)
			.then(res => {
				if (res.data.success) {
					emit("deleted", res.data.sigma_queries[0])
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

onBeforeMount(() => {
	setModel()
})
</script>
