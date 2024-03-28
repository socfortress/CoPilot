<template>
	<div class="item flex flex-col gap-2 px-5 py-3">
		<div class="header-box flex justify-between gap-4">
			<div class="name">{{ alert.name }}</div>
			<div class="badge flex mb-2">
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
			</div>
		</div>
		<div class="main-box flex justify-between gap-4">
			<div class="content">{{ alert.value }}</div>
			<div class="actions-box">
				<n-button
					v-if="!isEnabled"
					:loading="loadingProvision"
					type="success"
					secondary
					@click="openFormDialog()"
				>
					<template #icon><Icon :name="EnableIcon"></Icon></template>
					Enable
				</n-button>
			</div>
		</div>
		<div class="footer-box flex justify-between items-center gap-4">
			<div class="actions-box">
				<n-button
					v-if="!isEnabled"
					:loading="loadingProvision"
					type="success"
					secondary
					size="small"
					@click="openFormDialog()"
				>
					<template #icon><Icon :name="EnableIcon"></Icon></template>
					Enable
				</n-button>
			</div>
		</div>

		<n-modal
			:title="alert.name"
			v-model:show="showFormDialog"
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
							:min="1"
							v-model:value="formModel.searchWithinLast"
							@keydown.enter.prevent
							placeholder="Input time in seconds"
							clearable
							class="w-full"
						/>
					</n-form-item>
					<n-form-item path="executeEvery" label="Execute Every (time in seconds)">
						<n-input-number
							:min="1"
							v-model:value="formModel.executeEvery"
							@keydown.enter.prevent
							placeholder="Input time in seconds"
							clearable
							class="w-full"
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
import type { AvailableMonitoringAlert } from "@/types/monitoringAlerts.d"
import { ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import {
	NButton,
	NSpin,
	useMessage,
	NModal,
	type FormRules,
	NForm,
	NFormItem,
	NInputNumber,
	type FormValidationError
} from "naive-ui"
import Api from "@/api"
import type { ProvisionsMonitoringAlertParams } from "@/api/monitoringAlerts"

const emit = defineEmits<{
	(e: "provisioned"): void
}>()

const { alert, isEnabled } = defineProps<{ alert: AvailableMonitoringAlert; isEnabled: boolean }>()

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

<style lang="scss" scoped>
.item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-050);

	.header-box {
		font-size: 13px;

		.name {
			font-family: var(--font-family-mono);
			word-break: break-word;
			color: var(--fg-secondary-color);
		}
	}
	.main-box {
		.content {
			word-break: break-word;
		}
	}

	.footer-box {
		display: none;
		font-size: 13px;
		margin-top: 10px;
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}

	@container (max-width: 450px) {
		.main-box {
			.actions-box {
				display: none;
			}
		}
		.footer-box {
			display: flex;
		}
	}
}
</style>
