<template>
	<n-spin :show="loading" class="flex flex-col">
		<div class="header flex items-center justify-end gap-2">
			<div class="info flex grow gap-5">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-default rounded-lg">
							<n-button size="small" class="!cursor-help">
								<template #icon>
									<Icon :name="InfoIcon"></Icon>
								</template>
							</n-button>
						</div>
					</template>
					<div class="flex flex-col gap-2">
						<div class="box">
							Total:
							<code>{{ total }}</code>
						</div>
						<div class="box">
							Running:
							<code>{{ totalRunning }}</code>
						</div>
					</div>
				</n-popover>
			</div>
			<n-select
				v-model:value="stateFilter"
				:options="stateOptions"
				clearable
				placeholder="State..."
				size="small"
				style="width: 125px"
			/>
		</div>
		<n-scrollbar class="my-3">
			<div class="list flex min-h-52 flex-col gap-2">
				<template v-if="itemsFiltered.length">
					<InputItem
						v-for="input of itemsFiltered"
						:key="input.id"
						embedded
						:input="input"
						@updated="getData('running')"
					/>
				</template>
				<template v-else>
					<n-empty v-if="!loading" description="No items found" class="h-48 justify-center" />
				</template>
			</div>
		</n-scrollbar>
	</n-spin>
</template>

<script setup lang="ts">
import type { ConfiguredInput, InputExtended, RunningInput } from "@/types/graylog/inputs.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { NButton, NEmpty, NPopover, NScrollbar, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import InputItem from "./Item.vue"

const InfoIcon = "carbon:information"

const message = useMessage()
const loading = ref(false)
const configuredInputs = ref<ConfiguredInput[]>([])
const runningInputs = ref<RunningInput[]>([])

const total = computed(() => configuredInputs.value.length)
const totalRunning = computed(() => runningInputs.value.length)

const stateFilter = ref<null | number>(null)
const stateOptions = [
	{ label: "Not Running", value: 0 },
	{ label: "Running", value: 1 }
]

const itemsSanitized = computed<InputExtended[]>(() => {
	return configuredInputs.value.map(c => {
		const runItem = runningInputs.value.find(r => r.id === c.id)
		const res = c as InputExtended

		res.state = runItem?.state || ""
		res.started_at = runItem?.started_at || ""
		res.detailed_message = runItem?.detailed_message || null

		return res
	})
})

const itemsFiltered = computed(() => {
	return itemsSanitized.value.filter(o => {
		switch (stateFilter.value) {
			case 1:
				return o.state === "RUNNING"
			case 0:
				return o.state === ""
			default:
				return true
		}
	})
})

function getData(type: "configured" | "running") {
	loading.value = true

	const endpoint = type === "configured" ? "getInputsConfigured" : "getInputsRunning"

	Api.graylog[endpoint]()
		.then(res => {
			if (res.data.success) {
				const data = res.data as {
					configured_inputs?: ConfiguredInput[]
					running_inputs?: RunningInput[]
				}

				if (data.configured_inputs !== undefined) {
					configuredInputs.value = data?.configured_inputs || []
				}
				if (data.running_inputs !== undefined) {
					runningInputs.value = data?.running_inputs || []
				}
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

onBeforeMount(() => {
	getData("configured")
	getData("running")
})
</script>

<style lang="scss" scoped>
.n-spin-container {
	height: 100%;
	max-height: 100%;
	overflow: hidden;
	box-sizing: border-box;

	:deep() {
		.n-spin-content {
			height: 100%;
			box-sizing: border-box;
			display: flex;
			flex-direction: column;
		}
	}
}

.header {
	padding: var(--n-header-padding);
	box-sizing: border-box;
	padding-bottom: 0;
}
.list {
	padding: var(--n-body-padding);
	padding-top: 0;
	padding-bottom: 0;
}
</style>
