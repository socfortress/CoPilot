<template>
	<div>
		<CardEntity hoverable>
			<template #header>{{ alert.name }}</template>
			<template #default>{{ alert.value }}</template>
			<template #footerMain>
				<Badge :type="isEnabled ? 'active' : 'muted'">
					<template #iconRight>
						<Icon :name="isEnabled ? EnabledIcon : DisabledIcon" :size="13"></Icon>
					</template>
					<template #label>
						<span class="whitespace-nowrap">
							{{ isEnabled ? "Enabled" : "Not Enabled" }}
						</span>
					</template>
				</Badge>
			</template>
			<template #footerExtra>
				<n-button
					v-if="!isEnabled"
					:loading="loadingProvision"
					type="success"
					size="small"
					secondary
					@click="openFormDialog()"
				>
					<template #icon>
						<Icon :name="EnableIcon"></Icon>
					</template>
					Enable
				</n-button>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showFormDialog"
			:title="alert.name"
			preset="card"
			segmented
			:mask-closable="false"
			:close-on-esc="false"
			:style="{ maxWidth: 'min(500px, 90vw)', minHeight: 'min(350px, 90vh)', overflow: 'hidden' }"
		>
			<n-spin :show="loadingProvision">
				<n-form ref="formRef" :model="formModel" :rules="formRules">
					<n-form-item path="searchWithinLast" label="Search Within Last (time in seconds)">
						<n-input-number
							v-model:value="formModel.searchWithinLast"
							:min="1"
							placeholder="Input time in seconds"
							clearable
							class="w-full"
							@keydown.enter.prevent
						/>
					</n-form-item>
					<n-form-item path="executeEvery" label="Execute Every (time in seconds)">
						<n-input-number
							v-model:value="formModel.executeEvery"
							:min="1"
							placeholder="Input time in seconds"
							clearable
							class="w-full"
							@keydown.enter.prevent
						/>
					</n-form-item>
				</n-form>
			</n-spin>
			<template #footer>
				<div class="flex justify-end gap-3">
					<n-button @click="closeFormDialog()">Close</n-button>
					<n-button :loading="loadingProvision" type="success" @click="validateForm">Enable</n-button>
				</div>
			</template>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ProvisionsMonitoringAlertParams } from "@/api/endpoints/monitoringAlerts"
import type { AvailableMonitoringAlert } from "@/types/monitoringAlerts.d"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import {
	type FormRules,
	type FormValidationError,
	NButton,
	NForm,
	NFormItem,
	NInputNumber,
	NModal,
	NSpin,
	useMessage
} from "naive-ui"
import { ref } from "vue"

const { alert, isEnabled } = defineProps<{ alert: AvailableMonitoringAlert; isEnabled: boolean }>()

const emit = defineEmits<{
	(e: "provisioned"): void
}>()

const DisabledIcon = "carbon:subtract"
const EnabledIcon = "ph:check-bold"
const EnableIcon = "carbon:play"

const loadingProvision = ref(false)
const showFormDialog = ref(false)
const message = useMessage()

const formRef = ref()
const formModel = ref<{ searchWithinLast: null | number; executeEvery: null | number }>(getClearFormModel())
const formRules: FormRules = {
	searchWithinLast: [
		{
			required: true
		}
	],
	executeEvery: [
		{
			required: true
		}
	]
}

function getClearFormModel() {
	return {
		searchWithinLast: null,
		executeEvery: null
	}
}

function resetFormModel() {
	formModel.value = getClearFormModel()
}

function openFormDialog() {
	resetFormModel()
	showFormDialog.value = true
}

function closeFormDialog() {
	resetFormModel()
	showFormDialog.value = false
}

function validateForm(e: MouseEvent) {
	e.preventDefault()
	formRef.value?.validate((errors: Array<FormValidationError> | undefined) => {
		if (!errors) {
			provisionsMonitoringAlert()
		} else {
			for (const err of errors) {
				message.error(err[0].message || "Invalid fields")
			}
		}
	})
}

function provisionsMonitoringAlert() {
	if (formModel.value.searchWithinLast && formModel.value.executeEvery) {
		loadingProvision.value = true

		const params: ProvisionsMonitoringAlertParams = {
			searchWithinLast: formModel.value.searchWithinLast,
			executeEvery: formModel.value.executeEvery
		}

		Api.monitoringAlerts
			.provisionsMonitoringAlert(alert.name, params)
			.then(res => {
				if (res.data.success) {
					message.success(res.data?.message || `Monitoring alert ${alert.name} provisioned successfully`)
					emit("provisioned")
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				loadingProvision.value = false
			})
	}
}
</script>
