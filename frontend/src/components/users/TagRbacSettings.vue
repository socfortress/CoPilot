<template>
    <n-card title="Tag-Based Access Control" size="small">
        <template #header-extra>
            <n-tag :type="settings.enabled ? 'success' : 'default'" size="small">
                {{ settings.enabled ? "Enabled" : "Disabled" }}
            </n-tag>
        </template>

        <n-spin :show="loading">
            <div class="settings-form">
                <n-form-item label="Enable Tag RBAC">
                    <n-switch v-model:value="settings.enabled" @update:value="handleSettingsChange">
                        <template #checked>On</template>
                        <template #unchecked>Off</template>
                    </n-switch>
                </n-form-item>

                <n-form-item label="Untagged Alert Visibility" v-if="settings.enabled">
                    <n-radio-group
                        v-model:value="settings.untagged_alert_behavior"
                        @update:value="handleSettingsChange"
                    >
                        <n-space vertical>
                            <n-radio value="visible">
                                <div class="radio-label">
                                    <span class="label">Visible to All</span>
                                    <span class="description">Users can see alerts without tags</span>
                                </div>
                            </n-radio>
                            <n-radio value="hidden">
                                <div class="radio-label">
                                    <span class="label">Hidden</span>
                                    <span class="description">Users can only see alerts with assigned tags</span>
                                </div>
                            </n-radio>
                        </n-space>
                    </n-radio-group>
                </n-form-item>

                <n-divider v-if="settings.enabled" />

                <n-alert v-if="settings.enabled" type="info" title="How Tag RBAC Works">
                    <ul class="info-list">
                        <li>Users with <strong>no tag restrictions</strong> can see all alerts</li>
                        <li>Users with <strong>assigned tags</strong> can only see alerts with those tags</li>
                        <li>Admins and Schedulers always have full access</li>
                        <li>Customer access rules still apply in addition to tag rules</li>
                    </ul>
                </n-alert>

                <div class="actions" v-if="hasChanges">
                    <n-button type="primary" :loading="saving" @click="saveSettings">
                        Save Settings
                    </n-button>
                    <n-button @click="resetSettings">Cancel</n-button>
                </div>
            </div>
        </n-spin>
    </n-card>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue"
import {
    NCard,
    NForm,
    NFormItem,
    NSwitch,
    NRadioGroup,
    NRadio,
    NSpace,
    NButton,
    NTag,
    NAlert,
    NDivider,
    NSpin,
    useMessage
} from "naive-ui"
import type { TagAccessSettings } from "@/types/incidentManagement/tags.d"
import Api from "@/api"

const message = useMessage()

const loading = ref(false)
const saving = ref(false)

const settings = reactive<TagAccessSettings>({
    enabled: false,
    untagged_alert_behavior: "visible"
})

const originalSettings = ref<TagAccessSettings>({
    enabled: false,
    untagged_alert_behavior: "visible"
})

const hasChanges = computed(() => {
    return (
        settings.enabled !== originalSettings.value.enabled ||
        settings.untagged_alert_behavior !== originalSettings.value.untagged_alert_behavior
    )
})

async function loadSettings() {
    loading.value = true
    try {
        const res = await Api.tagRbac.getSettings()
        if (res.data.success) {
            settings.enabled = res.data.settings.enabled
            settings.untagged_alert_behavior = res.data.settings.untagged_alert_behavior
            originalSettings.value = { ...res.data.settings }
        }
    } catch (error) {
        console.error("Failed to load settings:", error)
    } finally {
        loading.value = false
    }
}

async function saveSettings() {
    saving.value = true
    try {
        const res = await Api.tagRbac.updateSettings(settings)
        if (res.data.success) {
            message.success("Tag RBAC settings saved")
            originalSettings.value = { ...settings }
        } else {
            message.error(res.data.message || "Failed to save settings")
        }
    } catch (error: any) {
        message.error(error.response?.data?.message || "Failed to save settings")
    } finally {
        saving.value = false
    }
}

function resetSettings() {
    settings.enabled = originalSettings.value.enabled
    settings.untagged_alert_behavior = originalSettings.value.untagged_alert_behavior
}

function handleSettingsChange() {
    // This triggers reactivity for computed hasChanges
}

onMounted(() => {
    loadSettings()
})
</script>

<style scoped lang="scss">
.settings-form {
    .radio-label {
        display: flex;
        flex-direction: column;

        .label {
            font-weight: 500;
        }

        .description {
            font-size: 12px;
            opacity: 0.7;
        }
    }

    .info-list {
        margin: 0;
        padding-left: 20px;

        li {
            margin-bottom: 4px;
        }
    }

    .actions {
        display: flex;
        gap: 12px;
        margin-top: 16px;
    }
}
</style>
