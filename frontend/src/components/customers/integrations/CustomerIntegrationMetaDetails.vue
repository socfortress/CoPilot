<template>
	<div class="flex flex-col">
		<n-spin :show="loading" content-class="flex grow flex-col">
			<div v-if="metaData" class="flex min-h-80 grow flex-col justify-between gap-5">
				<!-- Edit Form (when editing) -->
				<div v-if="isEditing" class="flex flex-col gap-4">
					<n-form ref="formRef" :model="editForm" :rules="rules" label-placement="left" label-width="auto">
						<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
							<!-- Customer Code (readonly) -->
							<n-form-item label="Customer Code" path="customer_code">
								<n-input v-model:value="editForm.customer_code" readonly />
							</n-form-item>

							<!-- Integration Name (readonly) -->
							<n-form-item label="Integration Name" path="integration_name">
								<n-input v-model:value="editForm.integration_name" readonly />
							</n-form-item>

							<!-- Graylog Fields -->
							<n-form-item label="Graylog Input ID" path="graylog_input_id">
								<n-input v-model:value="editForm.graylog_input_id" placeholder="Optional" />
							</n-form-item>

							<n-form-item label="Graylog Index ID" path="graylog_index_id">
								<n-input v-model:value="editForm.graylog_index_id" placeholder="Optional" />
							</n-form-item>

							<n-form-item label="Graylog Stream ID" path="graylog_stream_id">
								<n-input v-model:value="editForm.graylog_stream_id" placeholder="Optional" />
							</n-form-item>

							<n-form-item label="Graylog Pipeline ID" path="graylog_pipeline_id">
								<n-input v-model:value="editForm.graylog_pipeline_id" placeholder="Optional" />
							</n-form-item>

							<n-form-item label="Graylog Content Pack Input ID" path="graylog_content_pack_input_id">
								<n-input v-model:value="editForm.graylog_content_pack_input_id" placeholder="Optional" />
							</n-form-item>

							<n-form-item label="Graylog Content Pack Stream ID" path="graylog_content_pack_stream_id">
								<n-input v-model:value="editForm.graylog_content_pack_stream_id" placeholder="Optional" />
							</n-form-item>

							<!-- Grafana Fields -->
							<n-form-item label="Grafana Org ID" path="grafana_org_id">
								<n-input v-model:value="editForm.grafana_org_id" placeholder="Optional" />
							</n-form-item>

							<n-form-item label="Grafana Dashboard Folder ID" path="grafana_dashboard_folder_id">
								<n-input v-model:value="editForm.grafana_dashboard_folder_id" placeholder="Optional" />
							</n-form-item>

							<n-form-item label="Grafana Datasource UID" path="grafana_datasource_uid">
								<n-input v-model:value="editForm.grafana_datasource_uid" placeholder="Optional" />
							</n-form-item>
						</div>
					</n-form>

					<!-- Edit Form Actions -->
					<div class="flex justify-end gap-3">
						<n-button @click="cancelEdit">Cancel</n-button>
						<n-button type="primary" :loading="updating" @click="saveChanges">
							<template #icon>
								<Icon :name="SaveIcon"></Icon>
							</template>
							Save Changes
						</n-button>
					</div>
				</div>

				<!-- Read-only View (when not editing) -->
				<div v-else class="grid-auto-fit-200 grid gap-2">
					<CardKV v-for="item of metaItems" :key="item.key">
						<template #key>
							{{ item.label }}
						</template>
						<template #value>
							<code class="text-xs">{{ item.value || "-" }}</code>
						</template>
					</CardKV>
				</div>

				<!-- Bottom Actions -->
				<div class="flex items-center justify-between">
					<Badge :type="metaData.table_type === 'network_connector' ? 'info' : 'success'">
						<template #value>
							{{ metaData.table_type === 'network_connector' ? 'Network Connector' : 'Integration' }}
						</template>
					</Badge>

					<div class="flex gap-3">
						<n-button v-if="!isEditing" secondary @click="startEdit">
							<template #icon>
								<Icon :name="EditIcon"></Icon>
							</template>
							Edit
						</n-button>

						<n-button secondary @click="loadMetaData()">
							<template #icon>
								<Icon :name="RefreshIcon"></Icon>
							</template>
							Refresh
						</n-button>
					</div>
				</div>
			</div>

			<div v-else-if="!loading" class="flex min-h-80 items-center justify-center">
				<n-empty description="No metadata found" />
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { FormInst, FormRules } from "naive-ui"
import type { UpdateMetaAutoRequest } from "@/api/endpoints/integrations"
import type { CustomerIntegrationMetaResponse } from "@/types/integrations.d"
import { NButton, NEmpty, NForm, NFormItem, NInput, NSpin, useMessage } from "naive-ui"
import { computed, onMounted, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
    customerCode: string
    integrationName: string
}>()

const RefreshIcon = "carbon:refresh"
const EditIcon = "carbon:edit"
const SaveIcon = "carbon:save"

const message = useMessage()
const loading = ref(false)
const updating = ref(false)
const isEditing = ref(false)
const metaData = ref<CustomerIntegrationMetaResponse | null>(null)
const formRef = ref<FormInst | null>(null)

// Form for editing
const editForm = ref<UpdateMetaAutoRequest>({
    customer_code: props.customerCode,
    integration_name: props.integrationName
})

// Form validation rules
const rules: FormRules = {
    customer_code: {
        required: true,
        message: "Customer code is required",
        trigger: ["input", "blur"]
    },
    integration_name: {
        required: true,
        message: "Integration name is required",
        trigger: ["input", "blur"]
    }
}

const metaItems = computed(() => {
    if (!metaData.value?.data) return []

    const data = metaData.value.data
    const items = []

    // Common fields
    if (data.id) items.push({ key: 'id', label: 'ID', value: data.id })
    if (data.customer_code) items.push({ key: 'customer_code', label: 'Customer Code', value: data.customer_code })

    // Integration name fields
    if (data.integration_name) items.push({ key: 'integration_name', label: 'Integration Name', value: data.integration_name })
    if (data.network_connector_name) items.push({ key: 'network_connector_name', label: 'Network Connector Name', value: data.network_connector_name })

    // Graylog fields
    if (data.graylog_input_id) items.push({ key: 'graylog_input_id', label: 'Graylog Input ID', value: data.graylog_input_id })
    if (data.graylog_index_id) items.push({ key: 'graylog_index_id', label: 'Graylog Index ID', value: data.graylog_index_id })
    if (data.graylog_stream_id) items.push({ key: 'graylog_stream_id', label: 'Graylog Stream ID', value: data.graylog_stream_id })
    if (data.graylog_pipeline_id) items.push({ key: 'graylog_pipeline_id', label: 'Graylog Pipeline ID', value: data.graylog_pipeline_id })
    if (data.graylog_content_pack_input_id) items.push({ key: 'graylog_content_pack_input_id', label: 'Graylog Content Pack Input ID', value: data.graylog_content_pack_input_id })
    if (data.graylog_content_pack_stream_id) items.push({ key: 'graylog_content_pack_stream_id', label: 'Graylog Content Pack Stream ID', value: data.graylog_content_pack_stream_id })

    // Grafana fields
    if (data.grafana_org_id) items.push({ key: 'grafana_org_id', label: 'Grafana Org ID', value: data.grafana_org_id })
    if (data.grafana_dashboard_folder_id) items.push({ key: 'grafana_dashboard_folder_id', label: 'Grafana Dashboard Folder ID', value: data.grafana_dashboard_folder_id })
    if (data.grafana_datasource_uid) items.push({ key: 'grafana_datasource_uid', label: 'Grafana Datasource UID', value: data.grafana_datasource_uid })

    return items
})

function loadMetaData() {
    loading.value = true

    Api.integrations
        .getMetaAuto(props.customerCode, props.integrationName)
        .then(res => {
            if (res.data.success) {
                metaData.value = {
                    data: res.data.data,
                    table_type: res.data.table_type
                }
            } else {
                message.warning(res.data?.message || "Failed to load metadata")
                metaData.value = null
            }
        })
        .catch(err => {
            const errorMsg = err.response?.data?.message || "An error occurred while loading metadata"
            message.error(errorMsg)
            metaData.value = null
        })
        .finally(() => {
            loading.value = false
        })
}

function startEdit() {
    if (!metaData.value?.data) return

    const data = metaData.value.data
    // Pre-populate the form with current values
    editForm.value = {
        customer_code: props.customerCode,
        integration_name: props.integrationName,
        graylog_input_id: data.graylog_input_id || "",
        graylog_index_id: data.graylog_index_id || "",
        graylog_stream_id: data.graylog_stream_id || "",
        graylog_pipeline_id: data.graylog_pipeline_id || "",
        graylog_content_pack_input_id: data.graylog_content_pack_input_id || "",
        graylog_content_pack_stream_id: data.graylog_content_pack_stream_id || "",
        grafana_org_id: data.grafana_org_id || "",
        grafana_dashboard_folder_id: data.grafana_dashboard_folder_id || "",
        grafana_datasource_uid: data.grafana_datasource_uid || ""
    }
    isEditing.value = true
}

function cancelEdit() {
    isEditing.value = false
    // Reset form to original values
    if (metaData.value?.data) {
        startEdit()
        isEditing.value = false
    }
}

function saveChanges() {
    if (!formRef.value) return

    formRef.value.validate(errors => {
        if (errors) {
            message.error("Please fix the validation errors")
            return
        }

        updating.value = true

        // Create payload, excluding empty strings (treat as undefined)
        const payload: UpdateMetaAutoRequest = {
            customer_code: editForm.value.customer_code,
            integration_name: editForm.value.integration_name
        }

        // Add optional fields only if they have values
        if (editForm.value.graylog_input_id?.trim()) payload.graylog_input_id = editForm.value.graylog_input_id.trim()
        if (editForm.value.graylog_index_id?.trim()) payload.graylog_index_id = editForm.value.graylog_index_id.trim()
        if (editForm.value.graylog_stream_id?.trim()) payload.graylog_stream_id = editForm.value.graylog_stream_id.trim()
        if (editForm.value.graylog_pipeline_id?.trim()) payload.graylog_pipeline_id = editForm.value.graylog_pipeline_id.trim()
        if (editForm.value.graylog_content_pack_input_id?.trim()) payload.graylog_content_pack_input_id = editForm.value.graylog_content_pack_input_id.trim()
        if (editForm.value.graylog_content_pack_stream_id?.trim()) payload.graylog_content_pack_stream_id = editForm.value.graylog_content_pack_stream_id.trim()
        if (editForm.value.grafana_org_id?.trim()) payload.grafana_org_id = editForm.value.grafana_org_id.trim()
        if (editForm.value.grafana_dashboard_folder_id?.trim()) payload.grafana_dashboard_folder_id = editForm.value.grafana_dashboard_folder_id.trim()
        if (editForm.value.grafana_datasource_uid?.trim()) payload.grafana_datasource_uid = editForm.value.grafana_datasource_uid.trim()

        Api.integrations
            .updateMetaAuto(payload)
            .then(res => {
                if (res.data.success) {
                    message.success(res.data?.message || "Metadata updated successfully")
                    isEditing.value = false
                    // Reload the data to show updated values
                    loadMetaData()
                } else {
                    message.warning(res.data?.message || "Failed to update metadata")
                }
            })
            .catch(err => {
                const errorMsg = err.response?.data?.message || "An error occurred while updating metadata"
                message.error(errorMsg)
            })
            .finally(() => {
                updating.value = false
            })
    })
}

onMounted(() => {
    loadMetaData()
})
</script>
