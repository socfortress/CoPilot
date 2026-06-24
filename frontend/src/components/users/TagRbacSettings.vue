<template>
	<n-spin :show="loading">
		<div class="flex flex-col gap-4">
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
							<div class="flex flex-col">
								<span class="font-medium">Visible to All</span>
								<span class="text-xs opacity-70">Users can see alerts without tags</span>
							</div>
						</n-radio>
						<n-radio value="admin_only">
							<div class="flex flex-col">
								<span class="font-medium">Admin Only</span>
								<span class="text-xs opacity-70">Only admins can see untagged alerts</span>
							</div>
						</n-radio>
						<n-radio value="default_tag">
							<div class="flex flex-col">
								<span class="font-medium">Default Tag</span>
								<span class="text-xs opacity-70">
									Assign untagged alerts to users with a specific tag
								</span>
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
				<template #feedback>
					<span class="text-xs opacity-70">Users with access to this tag will also see untagged alerts</span>
				</template>
			</n-form-item>

			<n-divider v-if="settings.enabled" class="my-2!" />

			<n-alert v-if="settings.enabled" type="info" title="How Tag RBAC Works">
				<div>
					<p class="m-0 mb-3 font-medium">
						Tag RBAC controls which alerts users can see based on assigned tags.
					</p>

					<div class="mb-3">
						<strong class="mb-1 block">User Access Rules:</strong>
						<ul class="m-0 pl-5">
							<li class="mb-1">
								<strong>No tags assigned</strong>
								→ User can see
								<em class="not-italic underline">all alerts</em>
								(no restrictions)
							</li>
							<li class="mb-1">
								<strong>Tags assigned</strong>
								→ User can
								<em class="not-italic underline">only</em>
								see alerts with matching tags
							</li>
							<li class="mb-1">
								<strong>Admins &amp; Schedulers</strong>
								→ Always have full access
							</li>
						</ul>
					</div>

					<div class="mb-3">
						<strong class="mb-1 block">Untagged Alert Behavior:</strong>
						<ul class="m-0 pl-5">
							<li class="mb-1">
								<strong>Visible to All:</strong>
								Everyone sees untagged alerts
							</li>
							<li class="mb-1">
								<strong>Admin Only:</strong>
								Only admins see untagged alerts
							</li>
							<li class="mb-1">
								<strong>Default Tag:</strong>
								Users with the selected tag can see untagged alerts
							</li>
						</ul>
					</div>

					<n-divider class="my-3!" />

					<div class="rounded bg-black/5 p-2.5">
						<strong class="mb-1 block">Example:</strong>
						<p class="m-0 text-[13px] leading-normal">
							If analyst "John" is assigned the tag "Network", John will only see alerts tagged "Network".
							If untagged behavior is set to "Admin Only", John won't see any untagged alerts. If set to
							"Default Tag: Network", John will also see untagged alerts.
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
import type { ApiError } from "@/types/common"
import type { AlertTag } from "@/types/tags"
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
import { computed, onBeforeMount, reactive, ref, watch } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"

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
	availableTags.value.map((tag: AlertTag) => ({
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
		message.error(getApiErrorMessage(error as ApiError) || "Failed to save settings")
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

onBeforeMount(async () => {
	await loadSettings()
	// Pre-load tags if default_tag is already selected
	if (settings.untagged_alert_behavior === "default_tag") {
		await loadAvailableTags()
	}
})
</script>
