<template>
	<n-spin :show="loading" content-class="flex grow flex-col">
		<div class="flex flex-col gap-4">
			<n-form ref="formRef" :model :rules label-width="auto">
				<div class="grid grid-cols-1 gap-x-6 gap-y-2 md:grid-cols-2">
					<!-- Customer Code (readonly) -->
					<n-form-item :label="getMetaFieldLabel('customer_code')" path="customer_code">
						<n-input :value="model.customer_code" disabled />
					</n-form-item>

					<!-- Integration Name (readonly) -->
					<n-form-item :label="getMetaFieldLabel('integration_name')" path="integration_name">
						<n-input :value="model.integration_name" disabled />
					</n-form-item>

					<template v-for="(_, key) of model" :key>
						<n-form-item
							v-if="!['customer_code', 'integration_name'].includes(key)"
							:label="getMetaFieldLabel(key)"
							:path="key"
						>
							<n-input v-model:value.trim="model[key]" placeholder="Optional" clearable />
						</n-form-item>
					</template>
				</div>
			</n-form>

			<!-- Edit Form Actions -->
			<div class="flex items-center justify-between gap-3">
				<div class="flex items-center justify-between gap-3">
					<slot name="extraActions" />

					<n-button v-if="showResetButton" @click="reset()">Reset</n-button>
				</div>
				<n-button type="primary" :loading="loading" @click="save()">
					<template #icon>
						<Icon :name="SaveIcon" />
					</template>
					Save Changes
				</n-button>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { FormInst, FormRules } from "naive-ui"
import type { UpdateMetaAutoRequest } from "@/api/endpoints/integrations"
import type { CustomerIntegrationMetaNetwork, CustomerIntegrationMetaThirdParty } from "@/types/integrations.d"
import { NButton, NForm, NFormItem, NInput, NSpin, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getMetaFieldLabel } from "./utils"

const { integrationData, showResetButton } = defineProps<{
	integrationData: CustomerIntegrationMetaThirdParty | CustomerIntegrationMetaNetwork
	showResetButton?: boolean
}>()

const emit = defineEmits<{
	(e: "success"): void
}>()

const SaveIcon = "carbon:save"

const message = useMessage()
const loading = ref(false)
const formRef = ref<FormInst | null>(null)

// Form for editing
const model = ref<UpdateMetaAutoRequest>(getDefaultModel(integrationData))

// Form validation rules
const rules: FormRules = {
	customer_code: {
		required: true
	},
	integration_name: {
		required: true
	}
}

function getDefaultModel(
	entity?: CustomerIntegrationMetaThirdParty | CustomerIntegrationMetaNetwork
): UpdateMetaAutoRequest {
	return {
		customer_code: entity?.customer_code || "",
		integration_name:
			entity && "integration_name" in entity
				? entity.integration_name
				: entity && "network_connector_name" in entity
					? entity.network_connector_name
					: "",
		graylog_input_id: entity?.graylog_input_id || undefined,
		graylog_index_id: entity?.graylog_index_id || undefined,
		graylog_stream_id: entity?.graylog_stream_id || undefined,
		graylog_pipeline_id: entity?.graylog_pipeline_id || undefined,
		graylog_content_pack_input_id: entity?.graylog_content_pack_input_id || undefined,
		graylog_content_pack_stream_id: entity?.graylog_content_pack_stream_id || undefined,
		grafana_org_id: entity?.grafana_org_id || undefined,
		grafana_dashboard_folder_id: entity?.grafana_dashboard_folder_id || undefined,
		grafana_datasource_uid: entity?.grafana_datasource_uid || undefined
	}
}

function reset() {
	if (!loading.value) {
		model.value = getDefaultModel(integrationData)
	}
}

function save() {
	if (!formRef.value) return

	formRef.value.validate(errors => {
		if (errors) {
			message.error("Please fix the validation errors")
			return
		}

		loading.value = true

		const payload: UpdateMetaAutoRequest = { ...model.value }
		for (const key in payload) {
			if (!payload[key as keyof UpdateMetaAutoRequest]) payload[key as keyof UpdateMetaAutoRequest] = ""
		}

		Api.integrations
			.updateMetaAuto(payload)
			.then(res => {
				if (res.data.success) {
					message.success(res.data?.message || "Metadata updated successfully")
					// Reload the data to show updated values
					emit("success")
				} else {
					message.warning(res.data?.message || "Failed to update metadata")
				}
			})
			.catch(err => {
				const errorMsg = err.response?.data?.message || "An error occurred while updating metadata"
				message.error(errorMsg)
			})
			.finally(() => {
				loading.value = false
			})
	})
}
</script>
