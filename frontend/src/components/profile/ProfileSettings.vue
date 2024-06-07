<template>
	<n-spin class="settings" :show="loading">
		<n-card>
			<n-form ref="formRef" :label-width="80" :model="formValue" :rules="formRules">
				<div class="title">General</div>
				<div class="flex flex-col md:flex-row md:gap-6">
					<n-form-item label="Date Format" path="dateFormat" class="basis-1/3">
						<n-select v-model:value="formValue.dateFormat" :options="dateFormatsAvailable" />
					</n-form-item>
					<n-form-item label="Time Format" path="hours24" class="basis-1/3">
						<n-radio-group v-model:value="formValue.hours24" name="radiogroup">
							<div class="flex flex-wrap gap-3">
								<n-radio :value="true" :label="`24 Hours [ ${h24} ]`" />
								<n-radio :value="false" :label="`12 Hours [ ${h12} ]`" />
							</div>
						</n-radio-group>
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
import { ref } from "vue"
import {
	NSpin,
	NCard,
	NForm,
	NFormItem,
	NButton,
	NSelect,
	NRadio,
	NRadioGroup,
	type FormValidationError,
	useMessage,
	type FormInst
} from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"

const settingsStore = useSettingsStore()

const h24 = dayjs().format("HH:mm")
const h12 = dayjs().format("h:mm a")
const dateFormatsAvailable = settingsStore.dateFormatsAvailable.map(i => ({ label: i, value: i }))
const currentSateFormat = settingsStore.rawDateFormat
const hours24 = settingsStore.hours24

const formValue = ref({
	dateFormat: currentSateFormat,
	hours24
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

			message.success("Settings saved")
		} else {
			message.error("Something was wrong")
		}
		loading.value = false
	})
}
</script>

<style lang="scss" scoped>
.settings {
	.title {
		font-size: 20px;
		margin-bottom: 20px;

		&:not(:first-child) {
			margin-top: 20px;
		}
	}
}
</style>
