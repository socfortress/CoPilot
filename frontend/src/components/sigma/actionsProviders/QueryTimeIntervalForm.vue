<template>
	<n-popover v-model:show="show" trigger="manual" to="body" content-class="px-0" @clickoutside="closePopup()">
		<template #trigger>
			<slot :loading :toggle-popup />
		</template>

		<div class="flex flex-col gap-4 py-1">
			<div class="flex items-center gap-2">
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
			</div>

			<div class="flex justify-between gap-2">
				<n-button quaternary size="small" @click="closePopup()">Close</n-button>
				<n-button
					:disabled="!dirty || !isValid"
					:loading
					type="primary"
					size="small"
					@click="updateTimeInterval()"
				>
					Save
				</n-button>
			</div>
		</div>
	</n-popover>
</template>

<script setup lang="ts">
import type { SigmaQuery, SigmaTimeInterval, SigmaTimeIntervalUnit } from "@/types/sigma.d"
import Api from "@/api"
import { NButton, NInputGroup, NInputNumber, NPopover, NSelect, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, toRefs, watch } from "vue"

const props = defineProps<{
	query: SigmaQuery
}>()

const emit = defineEmits<{
	(e: "updated", value: SigmaQuery): void
}>()

const { query } = toRefs(props)

const loading = defineModel<boolean | undefined>("loading", { default: false })

const show = ref(false)
const lastShow = ref(new Date().getTime())
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

function togglePopup() {
	if (new Date().getTime() - lastShow.value > 500) {
		show.value = !show.value
	}
}

function closePopup() {
	lastShow.value = new Date().getTime()
	show.value = false
}

function setModel() {
	if (query.value.time_interval) {
		timeUnit.value = (
			query.value.time_interval.match(/[a-z]/i)?.[0] || "m"
		).toLocaleLowerCase() as SigmaTimeIntervalUnit
		timeValue.value = Number.parseInt(query.value.time_interval.match(/\d+/)?.[0] || "1")

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
					emit("updated", res.data.sigma_queries[0])
					message.success(res.data?.message || "Sigma query updated successfully")
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
