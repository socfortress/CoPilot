<template>
    <div class="flex flex-col">
        <n-spin :show="loading" content-class="flex grow flex-col">
            <div v-if="metaData" class="flex min-h-80 grow flex-col justify-between gap-5">
                <div class="grid-auto-fit-200 grid gap-2">
                    <CardKV v-for="item of metaItems" :key="item.key">
                        <template #key>
                            {{ item.label }}
                        </template>
                        <template #value>
                            <code class="text-xs">{{ item.value || "-" }}</code>
                        </template>
                    </CardKV>
                </div>

                <div class="flex items-center justify-between">
                    <Badge :type="metaData.table_type === 'network_connector' ? 'info' : 'success'">
                        <template #value>
                            {{ metaData.table_type === 'network_connector' ? 'Network Connector' : 'Integration' }}
                        </template>
                    </Badge>

                    <n-button secondary @click="loadMetaData()">
                        <template #icon>
                            <Icon :name="RefreshIcon"></Icon>
                        </template>
                        Refresh
                    </n-button>
                </div>
            </div>

            <div v-else-if="!loading" class="flex min-h-80 items-center justify-center">
                <n-empty description="No metadata found" />
            </div>
        </n-spin>
    </div>
</template>

<script setup lang="ts">
import { NButton, NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, onMounted, ref } from "vue"
import Api from "@/api"
import type { CustomerIntegrationMetaResponse } from "@/types/integrations.d"
import Badge from "@/components/common/Badge.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
    customerCode: string
    integrationName: string
}>()

const RefreshIcon = "carbon:refresh"

const message = useMessage()
const loading = ref(false)
const metaData = ref<CustomerIntegrationMetaResponse | null>(null)

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

onMounted(() => {
    loadMetaData()
})
</script>
