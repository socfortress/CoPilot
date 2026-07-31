<template>
	<n-spin :show="loading">
		<n-card>
			<n-form ref="formRef" :label-width="80" :model="formValue" :rules="formRules">
				<div class="mt-5 mb-5 text-xl first:mt-0">General</div>
				<div class="flex flex-col md:flex-row md:gap-6">
					<n-form-item label="Date Format" path="dateFormat" class="basis-1/3">
						<n-select v-model:value="formValue.dateFormat" :options="dateFormatsAvailable" />
					</n-form-item>
					<n-form-item label="Time Format" path="hours24" class="basis-1/3">
						<n-radio-group v-model:value="formValue.hours24" name="radiogroup">
							<div class="flex flex-wrap gap-3">
								<n-radio value :label="`24 Hours [ ${h24} ]`" />
								<n-radio :value="false" :label="`12 Hours [ ${h12} ]`" />
							</div>
						</n-radio-group>
					</n-form-item>
				</div>

				<div class="mt-5 mb-5 text-xl">Global customers filter</div>
				<div class="flex flex-col md:flex-row md:gap-6">
					<n-form-item label="Live sync" path="customerFilterLiveSync" class="basis-2/3">
						<div class="flex flex-col gap-2">
							<n-switch v-model:value="formValue.customerFilterLiveSync">
								<template #checked>Enabled</template>
								<template #unchecked>Disabled</template>
							</n-switch>
							<div class="text-secondary text-sm">
								When enabled, every view that supports the global customers filter re-applies it — and
								reloads its data — as soon as you change the selection in the sidebar. When disabled,
								the global filter is only applied when you open the view.
							</div>
						</div>
					</n-form-item>
				</div>

				<n-form-item>
					<n-button type="primary" @click="save()">Save</n-button>
				</n-form-item>
			</n-form>
		</n-card>
	</n-spin>
</template>

<script setup lang="ts">
import type { FormInst, FormValidationError } from "naive-ui"
import { NButton, NCard, NForm, NFormItem, NRadio, NRadioGroup, NSelect, NSpin, NSwitch, useMessage } from "naive-ui"
import { ref } from "vue"
import { useCustomerFilterStore } from "@/stores/customer-filter"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"

const settingsStore = useSettingsStore()
const customerFilterStore = useCustomerFilterStore()

const h24 = dayjs().format("HH:mm")
const h12 = dayjs().format("h:mm a")
const dateFormatsAvailable = settingsStore.dateFormatsAvailable.map(i => ({ label: i, value: i }))
const currentSateFormat = settingsStore.rawDateFormat
const hours24 = settingsStore.hours24

const formValue = ref({
	dateFormat: currentSateFormat,
	hours24,
	customerFilterLiveSync: customerFilterStore.liveSync
})

const loading = ref(false)
const formRef = ref<FormInst | null>(null)
const message = useMessage()

const formRules = {
	username: {
		required: true,
		message: "Please input username",
		trigger: "blur"
	},
	email: {
		required: true,
		message: "Please input email",
		trigger: "blur"
	}
}

function save() {
	loading.value = true

	formRef.value?.validate((errors: Array<FormValidationError> | undefined) => {
		if (!errors) {
			settingsStore.setDateFormat(formValue.value.dateFormat)
			settingsStore.setHours24(formValue.value.hours24)
			customerFilterStore.setLiveSync(formValue.value.customerFilterLiveSync)

			message.success("Settings saved")
		} else {
			message.error("Something was wrong")
		}
		loading.value = false
	})
}
</script>
