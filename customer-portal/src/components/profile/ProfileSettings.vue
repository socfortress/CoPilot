<template>
	<n-spin class="settings" :show="loading">
		<n-card>
			<n-form ref="formRef" :label-width="80" :model="formValue" :rules="formRules">
				<div class="title">{{ $t("profile.settings.general") }}</div>
				<n-form-item :label="$t('common.language.label')" class="max-w-80" data-testid="profile-language">
					<div class="flex w-full flex-col gap-1">
						<LanguagePicker />
						<span class="text-secondary text-xs">
							{{ localesStore.canChoose ? $t("common.language.hint") : $t("common.language.englishOnly") }}
						</span>
					</div>
				</n-form-item>
				<div class="flex flex-col md:flex-row md:gap-6">
					<n-form-item :label="$t('profile.settings.dateFormat')" path="dateFormat" class="basis-1/3">
						<n-select v-model:value="formValue.dateFormat" :options="dateFormatsAvailable" />
					</n-form-item>
					<n-form-item :label="$t('profile.settings.timeFormat')" path="hours24" class="basis-1/3">
						<n-radio-group v-model:value="formValue.hours24" name="radiogroup">
							<div class="flex flex-wrap gap-3">
								<n-radio value :label="$t('profile.settings.hours24', { time: h24 })" />
								<n-radio :value="false" :label="$t('profile.settings.hours12', { time: h12 })" />
							</div>
						</n-radio-group>
					</n-form-item>
				</div>

				<n-form-item>
					<n-button type="primary" @click="save()">{{ $t("common.actions.save") }}</n-button>
				</n-form-item>
			</n-form>
		</n-card>
	</n-spin>
</template>

<script setup lang="ts">
import type { FormInst, FormValidationError } from "naive-ui"
import { NButton, NCard, NForm, NFormItem, NRadio, NRadioGroup, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import { useI18n } from "vue-i18n"
import LanguagePicker from "@/components/common/LanguagePicker.vue"
import { useLocalesStore } from "@/stores/i18n"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"

const settingsStore = useSettingsStore()
const localesStore = useLocalesStore()
const { t } = useI18n()

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

const formRules = computed(() => ({
	username: {
		required: true,
		message: t("profile.settings.usernameRequired"),
		trigger: "blur"
	},
	email: {
		required: true,
		message: t("profile.settings.emailRequired"),
		trigger: "blur"
	}
}))

function save() {
	loading.value = true

	formRef.value?.validate((errors: Array<FormValidationError> | undefined) => {
		if (!errors) {
			settingsStore.setDateFormat(formValue.value.dateFormat)
			settingsStore.setHours24(formValue.value.hours24)

			message.success(t("profile.settings.saved"))
		} else {
			message.error(t("profile.settings.error"))
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
