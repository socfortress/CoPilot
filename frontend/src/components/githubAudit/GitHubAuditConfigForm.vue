<template>
	<n-drawer v-model:show="showDrawer" :width="600" placement="right">
		<n-drawer-content :title="isEdit ? 'Edit Configuration' : 'New GitHub Audit Configuration'" closable>
			<n-form ref="formRef" :model="formData" :rules="rules" label-placement="top">
				<n-divider title-placement="left">Basic Settings</n-divider>

				<n-form-item label="Customer" path="customer_code">
					<n-select
						v-model:value="formData.customer_code"
						placeholder="Select customer"
						:options="customerOptions"
						:disabled="isEdit"
						filterable
					/>
				</n-form-item>

				<n-form-item label="GitHub Organization" path="organization">
					<n-input v-model:value="formData.organization" placeholder="e.g., my-org" />
				</n-form-item>

				<n-form-item label="GitHub Token" path="github_token">
					<n-input
						v-model:value="formData.github_token"
						type="password"
						show-password-on="click"
						:placeholder="isEdit ? 'Leave blank to keep existing token' : 'ghp_xxxxxxxxxxxx'"
					/>
				</n-form-item>

				<n-form-item label="Token Type" path="token_type">
					<n-radio-group v-model:value="formData.token_type">
						<n-radio value="pat">Personal Access Token</n-radio>
						<n-radio value="app">GitHub App</n-radio>
					</n-radio-group>
				</n-form-item>

				<n-form-item label="Enabled">
					<n-switch v-model:value="formData.enabled" />
				</n-form-item>

				<n-divider title-placement="left">Audit Scope</n-divider>

				<n-grid :cols="2" :x-gap="16">
					<n-gi>
						<n-form-item label="Include Repositories">
							<n-switch v-model:value="formData.include_repos" />
						</n-form-item>
					</n-gi>
					<n-gi>
						<n-form-item label="Include Workflows">
							<n-switch v-model:value="formData.include_workflows" />
						</n-form-item>
					</n-gi>
					<n-gi>
						<n-form-item label="Include Members">
							<n-switch v-model:value="formData.include_members" />
						</n-form-item>
					</n-gi>
					<n-gi>
						<n-form-item label="Include Archived Repos">
							<n-switch v-model:value="formData.include_archived_repos" />
						</n-form-item>
					</n-gi>
				</n-grid>

				<n-form-item label="Repository Filter Mode">
					<n-radio-group v-model:value="formData.repo_filter_mode">
						<n-radio value="all">All Repositories</n-radio>
						<n-radio value="include">Include Only</n-radio>
						<n-radio value="exclude">Exclude</n-radio>
					</n-radio-group>
				</n-form-item>

				<n-form-item v-if="formData.repo_filter_mode !== 'all'" label="Repository List">
					<n-dynamic-tags v-model:value="formData.repo_filter_list" />
					<template #feedback>Enter repository names to {{ formData.repo_filter_mode }}</template>
				</n-form-item>

				<n-divider title-placement="left">Schedule</n-divider>

				<n-form-item label="Enable Scheduled Audits">
					<n-switch v-model:value="formData.auto_audit_enabled" />
				</n-form-item>

				<n-form-item v-if="formData.auto_audit_enabled" label="Schedule (Cron)" path="audit_schedule_cron">
					<n-input v-model:value="formData.audit_schedule_cron" placeholder="0 0 * * 1 (Weekly on Monday)" />
					<template #feedback>
						<n-text depth="3">
							Use cron format. Example: "0 0 * * 1" for weekly on Monday at midnight
						</n-text>
					</template>
				</n-form-item>

				<n-divider title-placement="left">Notifications</n-divider>

				<n-grid :cols="2" :x-gap="16">
					<n-gi>
						<n-form-item label="Notify on Critical">
							<n-switch v-model:value="formData.notify_on_critical" />
						</n-form-item>
					</n-gi>
					<n-gi>
						<n-form-item label="Notify on High">
							<n-switch v-model:value="formData.notify_on_high" />
						</n-form-item>
					</n-gi>
				</n-grid>

				<n-form-item label="Notification Webhook URL">
					<n-input v-model:value="formData.notification_webhook_url" placeholder="https://..." />
				</n-form-item>

				<n-form-item label="Notification Email">
					<n-input v-model:value="formData.notification_email" placeholder="security@example.com" />
				</n-form-item>

				<n-divider title-placement="left">Thresholds</n-divider>

				<n-form-item label="Minimum Passing Score">
					<n-slider v-model:value="formData.minimum_passing_score" :min="0" :max="100" :step="5" />
					<n-input-number
						v-model:value="formData.minimum_passing_score"
						:min="0"
						:max="100"
						style="width: 100px; margin-left: 16px"
					/>
				</n-form-item>
			</n-form>

			<template #footer>
				<div class="flex justify-end gap-3">
					<n-button @click="showDrawer = false">Cancel</n-button>
					<n-button type="primary" :loading="saving" @click="handleSubmit">
						{{ isEdit ? "Update" : "Create" }}
					</n-button>
				</div>
			</template>
		</n-drawer-content>
	</n-drawer>
</template>

<script setup lang="ts">
// TODO: refactor
import type { FormInst, FormRules } from "naive-ui"
import type { GitHubAuditConfig, GitHubAuditConfigCreate, GitHubAuditConfigUpdate } from "@/types/githubAudit.d"
import {
	NButton,
	NDivider,
	NDrawer,
	NDrawerContent,
	NDynamicTags,
	NForm,
	NFormItem,
	NGi,
	NGrid,
	NInput,
	NInputNumber,
	NRadio,
	NRadioGroup,
	NSelect,
	NSlider,
	NSwitch,
	NText,
	useMessage
} from "naive-ui"
import { computed, onMounted, reactive, ref, watch } from "vue"
import Api from "@/api"

const props = defineProps<{
	show: boolean
	config?: GitHubAuditConfig | null
}>()

const emit = defineEmits<{
	(e: "update:show", value: boolean): void
	(e: "saved"): void
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const saving = ref(false)
const customerOptions = ref<{ label: string; value: string }[]>([])

const showDrawer = computed({
	get: () => props.show,
	set: value => emit("update:show", value)
})

const isEdit = computed(() => !!props.config)

function defaultFormData(): GitHubAuditConfigCreate {
	return {
		customer_code: "",
		github_token: "",
		organization: "",
		token_type: "pat",
		enabled: true,
		auto_audit_enabled: false,
		audit_schedule_cron: null,
		include_repos: true,
		include_workflows: true,
		include_members: true,
		include_archived_repos: false,
		repo_filter_mode: "all",
		repo_filter_list: [],
		notify_on_critical: true,
		notify_on_high: false,
		notification_webhook_url: null,
		notification_email: null,
		minimum_passing_score: 70
	}
}

const formData = reactive<GitHubAuditConfigCreate>(defaultFormData())

const rules: FormRules = {
	customer_code: { required: true, message: "Customer is required", trigger: "blur" },
	organization: { required: true, message: "Organization is required", trigger: "blur" },
	github_token: {
		required: !isEdit.value,
		message: "GitHub token is required",
		trigger: "blur"
	}
}

watch(
	() => props.config,
	config => {
		if (config) {
			Object.assign(formData, {
				customer_code: config.customer_code,
				github_token: "",
				organization: config.organization,
				token_type: config.token_type,
				enabled: config.enabled,
				auto_audit_enabled: config.auto_audit_enabled,
				audit_schedule_cron: config.audit_schedule_cron,
				include_repos: config.include_repos,
				include_workflows: config.include_workflows,
				include_members: config.include_members,
				include_archived_repos: config.include_archived_repos,
				repo_filter_mode: config.repo_filter_mode,
				repo_filter_list: config.repo_filter_list || [],
				notify_on_critical: config.notify_on_critical,
				notify_on_high: config.notify_on_high,
				notification_webhook_url: config.notification_webhook_url,
				notification_email: config.notification_email,
				minimum_passing_score: config.minimum_passing_score
			})
		} else {
			Object.assign(formData, defaultFormData())
		}
	},
	{ immediate: true }
)

async function handleSubmit() {
	try {
		await formRef.value?.validate()
	} catch {
		return
	}

	saving.value = true
	try {
		if (isEdit.value && props.config) {
			const updateData: GitHubAuditConfigUpdate = { ...formData }
			if (!updateData.github_token) {
				delete updateData.github_token
			}
			await Api.githubAudit.updateConfig(props.config.id, updateData)
			message.success("Configuration updated successfully")
		} else {
			await Api.githubAudit.createConfig(formData)
			message.success("Configuration created successfully")
		}
		emit("saved")
		showDrawer.value = false
	} catch (error: any) {
		message.error(error.response?.data?.detail || "Failed to save configuration")
	} finally {
		saving.value = false
	}
}

onMounted(async () => {
	try {
		const response = await Api.customers.getCustomers()
		if (response.data.customers) {
			customerOptions.value = response.data.customers.map((c: any) => ({
				label: `${c.customer_name} (${c.customer_code})`,
				value: c.customer_code
			}))
		}
	} catch (error) {
		console.error("Failed to load customers:", error)
	}
})
</script>
