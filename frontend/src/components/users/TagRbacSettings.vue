<template>
	<n-spin :show="loading">
		<div class="settings-form flex flex-col gap-4">
			<n-form-item label="Enable Tag RBAC" :show-feedback="false">
				<n-switch v-model:value="settings.enabled">
					<template #checked>On</template>
					<template #unchecked>Off</template>
				</n-switch>
			</n-form-item>

			<n-form-item v-if="settings.enabled" label="Untagged Alert Visibility" :show-feedback="false">
				<n-radio-group v-model:value="settings.untagged_alert_behavior">
					<n-space vertical>
						<n-radio value="visible_to_all">
							<div class="radio-label">
								<span class="label">Visible to All</span>
								<span class="description">Users can see alerts without tags</span>
							</div>
						</n-radio>
						<n-radio value="admin_only">
							<div class="radio-label">
								<span class="label">Admin Only</span>
								<span class="description">Only admins can see untagged alerts</span>
							</div>
						</n-radio>
						<n-radio value="default_tag">
							<div class="radio-label">
								<span class="label">Default Tag</span>
								<span class="description">Assign untagged alerts to users with a specific tag</span>
							</div>
						</n-radio>
					</n-space>
				</n-radio-group>
			</n-form-item>

			<n-form-item
				v-if="settings.enabled && settings.untagged_alert_behavior === 'default_tag'"
				label="Default Tag"
				:show-feedback="false"
			>
				<n-select
					v-model:value="settings.default_tag_id"
					filterable
					clearable
					placeholder="Select a default tag"
					:options="tagOptions"
					:loading="loadingTags"
				/>
				<template #help>
					<span class="text-xs opacity-70">
						Users with access to this tag will also see untagged alerts
					</span>
				</template>
			</n-form-item>

			<n-divider v-if="settings.enabled" class="!my-2" />

			<n-alert v-if="settings.enabled" type="info" title="How Tag RBAC Works">
				<div class="info-content">
					<p class="intro">
						Tag RBAC controls which alerts users can see based on assigned tags.
					</p>

					<div class="section">
						<strong>User Access Rules:</strong>
						<ul class="info-list">
							<li>
								<strong>No tags assigned</strong> → User can see
								<em>all alerts</em> (no restrictions)
							</li>
							<li>
								<strong>Tags assigned</strong> → User can
								<em>only</em> see alerts with matching tags
							</li>
							<li>
								<strong>Admins &amp; Schedulers</strong> → Always have full access
							</li>
						</ul>
					</div>

					<div class="section">
						<strong>Untagged Alert Behavior:</strong>
						<ul class="info-list">
							<li>
								<strong>Visible to All:</strong> Everyone sees untagged alerts
							</li>
							<li>
								<strong>Admin Only:</strong> Only admins see untagged alerts
							</li>
							<li>
								<strong>Default Tag:</strong> Users with the selected tag can see untagged alerts
							</li>
						</ul>
					</div>

					<n-divider class="!my-3" />

					<div class="example">
						<strong>Example:</strong>
						<p>
							If analyst "John" is assigned the tag "Network", John will only see alerts tagged
							"Network". If untagged behavior is set to "Admin Only", John won't see any untagged
							alerts. If set to "Default Tag: Network", John will also see untagged alerts.
						</p>
					</div>
				</div>
			</n-alert>

			<div class="actions flex gap-3">
				<n-button type="primary" :loading="saving" :disabled="!hasChanges" @click="saveSettings">
					Save Settings
				</n-button>
				<n-button :disabled="!hasChanges" @click="resetSettings">Cancel</n-button>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { AlertTag } from "@/types/incidentManagement/tags.d"
import {
    NAlert,
    NButton,
    NDivider,
    NFormItem,
    NRadio,
    NRadioGroup,
    NSelect,
    NSpace,
    NSpin,
    NSwitch,
    useMessage
} from "naive-ui"
import { computed, onMounted, reactive, ref, watch } from "vue"
import Api from "@/api"

interface TagAccessSettings {
    enabled: boolean
    untagged_alert_behavior: "visible_to_all" | "admin_only" | "default_tag"
    default_tag_id: number | null
}

const message = useMessage()

const loading = ref(false)
const loadingTags = ref(false)
const saving = ref(false)
const availableTags = ref<AlertTag[]>([])

const settings = reactive<TagAccessSettings>({
    enabled: false,
    untagged_alert_behavior: "visible_to_all",
    default_tag_id: null
})

const originalSettings = ref<TagAccessSettings>({
    enabled: false,
    untagged_alert_behavior: "visible_to_all",
    default_tag_id: null
})

const tagOptions = computed(() =>
    availableTags.value.map(tag => ({
        label: tag.tag,
        value: tag.id
    }))
)

const hasChanges = computed(() => {
    return (
        settings.enabled !== originalSettings.value.enabled ||
        settings.untagged_alert_behavior !== originalSettings.value.untagged_alert_behavior ||
        settings.default_tag_id !== originalSettings.value.default_tag_id
    )
})

async function loadAvailableTags() {
    loadingTags.value = true
    try {
        const res = await Api.tagRbac.getAvailableTags()
        if (res.data.success) {
            availableTags.value = res.data.tags
        }
    } catch (error) {
        console.error("Failed to load available tags:", error)
    } finally {
        loadingTags.value = false
    }
}

async function loadSettings() {
    loading.value = true
    try {
        const res = await Api.tagRbac.getSettings()

        if (res.data.success && res.data.settings) {
            settings.enabled = res.data.settings.enabled
            settings.untagged_alert_behavior = res.data.settings.untagged_alert_behavior
            settings.default_tag_id = res.data.settings.default_tag_id
            originalSettings.value = {
                enabled: res.data.settings.enabled,
                untagged_alert_behavior: res.data.settings.untagged_alert_behavior,
                default_tag_id: res.data.settings.default_tag_id
            }
        }
    } catch (error) {
        console.error("Failed to load tag RBAC settings:", error)
        message.error("Failed to load Tag RBAC settings")
    } finally {
        loading.value = false
    }
}

async function saveSettings() {
    // Validate default_tag_id is set when using default_tag behavior
    if (settings.untagged_alert_behavior === "default_tag" && !settings.default_tag_id) {
        message.warning("Please select a default tag")
        return
    }

    saving.value = true
    try {
        const res = await Api.tagRbac.updateSettings({
            enabled: settings.enabled,
            untagged_alert_behavior: settings.untagged_alert_behavior,
            default_tag_id: settings.default_tag_id
        })

        if (res.data.success) {
            message.success("Tag RBAC settings saved")
            originalSettings.value = { ...settings }
        } else {
            message.error(res.data.message || "Failed to save settings")
        }
    } catch (error: any) {
        console.error("Failed to save settings:", error)
        message.error(error.response?.data?.message || "Failed to save settings")
    } finally {
        saving.value = false
    }
}

function resetSettings() {
    settings.enabled = originalSettings.value.enabled
    settings.untagged_alert_behavior = originalSettings.value.untagged_alert_behavior
    settings.default_tag_id = originalSettings.value.default_tag_id
}

// Load tags when default_tag behavior is selected
watch(
    () => settings.untagged_alert_behavior,
    newValue => {
        if (newValue === "default_tag" && availableTags.value.length === 0) {
            loadAvailableTags()
        }
    }
)

onMounted(async () => {
    await loadSettings()
    // Pre-load tags if default_tag is already selected
    if (settings.untagged_alert_behavior === "default_tag") {
        await loadAvailableTags()
    }
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

    .info-content {
        .intro {
            margin: 0 0 12px 0;
            font-weight: 500;
        }

        .section {
            margin-bottom: 12px;

            > strong {
                display: block;
                margin-bottom: 4px;
            }
        }

        .info-list {
            margin: 0;
            padding-left: 20px;

            li {
                margin-bottom: 4px;

                em {
                    font-style: normal;
                    text-decoration: underline;
                }
            }
        }

        .example {
            background: rgba(0, 0, 0, 0.05);
            border-radius: 4px;
            padding: 10px;

            > strong {
                display: block;
                margin-bottom: 4px;
            }

            p {
                margin: 0;
                font-size: 13px;
                line-height: 1.5;
            }
        }
    }
}
</style>
