<template>
	<n-form ref="formRef" :model="formData" :rules label-placement="left" label-width="160px">
		<n-form-item label="Name" path="name">
			<n-input v-model:value="formData.name" placeholder="Enter a friendly name for this schedule" />
		</n-form-item>

		<n-form-item label="Index Pattern" path="index_pattern">
			<n-input v-model:value="formData.index_pattern" placeholder="e.g., wazuh_customer_*" />
			<template #feedback>Use wildcards (*) to match multiple indices. Example: wazuh_customer_*</template>
		</n-form-item>

		<n-form-item label="Repository" path="repository">
			<n-select
				v-model:value="formData.repository"
				:options="repositoryOptions"
				placeholder="Select a repository"
				:loading="loadingRepositories"
			/>
		</n-form-item>

		<n-form-item label="Snapshot Prefix" path="snapshot_prefix">
			<n-input v-model:value="formData.snapshot_prefix" placeholder="e.g., scheduled" />
			<template #feedback>
				Prefix for generated snapshot names. Full name: {prefix}_{schedule_name}_{timestamp}
			</template>
		</n-form-item>

		<n-form-item label="Enabled" path="enabled">
			<n-switch v-model:value="formData.enabled" />
		</n-form-item>

		<n-form-item label="Skip Write Indices" path="skip_write_indices">
			<n-switch v-model:value="formData.skip_write_indices" />
			<span class="ml-2 text-sm text-gray-500">Skip indices currently being written to (recommended)</span>
		</n-form-item>

		<n-form-item label="Include Global State" path="include_global_state">
			<n-switch v-model:value="formData.include_global_state" />
		</n-form-item>

		<n-form-item label="Retention (Days)" path="retention_days">
			<n-input-number
				v-model:value="formData.retention_days"
				:min="1"
				:max="365"
				placeholder="Leave empty for no retention limit"
				clearable
				style="width: 100%"
			/>
			<template #feedback>
				Automatically delete snapshots older than this many days. Leave empty to keep forever.
			</template>
		</n-form-item>

		<n-divider title-placement="left">Schedule Window</n-divider>

		<n-form-item label="Scheduled Hour" path="scheduled_hour">
			<n-input-number
				v-model:value="formData.scheduled_hour"
				:min="0"
				:max="23"
				placeholder="Leave empty for any hour"
				clearable
				style="width: 100%"
			/>
			<template #feedback>
				Hour of day (0-23) when this schedule is allowed to run. Leave empty to allow any hour
				(legacy behavior — runs every poll).
			</template>
		</n-form-item>

		<n-form-item label="Scheduled Minute" path="scheduled_minute">
			<n-input-number
				v-model:value="formData.scheduled_minute"
				:min="0"
				:max="59"
				placeholder="Leave empty for any minute"
				clearable
				style="width: 100%"
				:disabled="formData.scheduled_hour == null"
			/>
			<template #feedback>
				Minute of hour. The schedule runs within a 15-minute tolerance window starting at
				this minute. Requires Scheduled Hour to be set.
			</template>
		</n-form-item>

		<n-form-item label="Interval (Days)" path="interval_days">
			<n-input-number
				v-model:value="formData.interval_days"
				:min="1"
				:max="365"
				style="width: 100%"
			/>
			<template #feedback>
				Minimum number of days between executions. Default 1 = at most once per day.
			</template>
		</n-form-item>

		<n-form-item label="Timezone" path="timezone">
			<n-select
				v-model:value="formData.timezone"
				:options="timezoneOptions"
				filterable
				tag
				placeholder="Select or type IANA timezone"
			/>
			<template #feedback>
				IANA timezone used to evaluate Scheduled Hour/Minute (e.g., UTC, America/New_York).
			</template>
		</n-form-item>

		<div class="mt-4 flex justify-end gap-2">
			<n-button @click="$emit('cancel')">Cancel</n-button>
			<n-button type="primary" :loading @click="handleSubmit">
				{{ isEditing ? "Update Schedule" : "Create Schedule" }}
			</n-button>
		</div>
	</n-form>
</template>

<script setup lang="ts">
// TODO-FE: refactor
import type { FormInst, FormRules, SelectOption } from "naive-ui"
import type { SnapshotRepository, SnapshotScheduleCreate, SnapshotScheduleResponse } from "@/types/snapshots.d"
import { NButton, NDivider, NForm, NFormItem, NInput, NInputNumber, NSelect, NSwitch, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"

const props = defineProps<{
	schedule?: SnapshotScheduleResponse | null
}>()

const emit = defineEmits<{
	(e: "success"): void
	(e: "cancel"): void
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const loading = ref(false)
const loadingRepositories = ref(false)
const repositories = ref<SnapshotRepository[]>([])

const isEditing = computed(() => !!props.schedule)

const formData = ref<SnapshotScheduleCreate>({
	name: "",
	index_pattern: "",
	repository: "",
	enabled: true,
	snapshot_prefix: "scheduled",
	include_global_state: false,
	skip_write_indices: true,
	retention_days: null,
	scheduled_hour: null,
	scheduled_minute: null,
	interval_days: 1,
	timezone: "UTC"
})

const repositoryOptions = computed<SelectOption[]>(() =>
	repositories.value.map(repo => ({
		label: repo.name,
		value: repo.name
	}))
)

const timezoneOptions: SelectOption[] = [
	{ label: "UTC", value: "UTC" },
	{ label: "America/New_York", value: "America/New_York" },
	{ label: "America/Chicago", value: "America/Chicago" },
	{ label: "America/Denver", value: "America/Denver" },
	{ label: "America/Los_Angeles", value: "America/Los_Angeles" },
	{ label: "Europe/London", value: "Europe/London" },
	{ label: "Europe/Berlin", value: "Europe/Berlin" },
	{ label: "Europe/Paris", value: "Europe/Paris" },
	{ label: "Asia/Tokyo", value: "Asia/Tokyo" },
	{ label: "Asia/Singapore", value: "Asia/Singapore" },
	{ label: "Australia/Sydney", value: "Australia/Sydney" }
]

const rules: FormRules = {
	name: {
		required: true,
		message: "Name is required",
		trigger: "blur"
	},
	index_pattern: {
		required: true,
		message: "Index pattern is required",
		trigger: "blur"
	},
	repository: {
		required: true,
		message: "Repository is required",
		trigger: "change"
	}
}

watch(
	() => props.schedule,
	newSchedule => {
		if (newSchedule) {
			formData.value = {
				name: newSchedule.name,
				index_pattern: newSchedule.index_pattern,
				repository: newSchedule.repository,
				enabled: newSchedule.enabled,
				snapshot_prefix: newSchedule.snapshot_prefix,
				include_global_state: newSchedule.include_global_state,
				skip_write_indices: newSchedule.skip_write_indices,
				retention_days: newSchedule.retention_days,
				scheduled_hour: newSchedule.scheduled_hour ?? null,
				scheduled_minute: newSchedule.scheduled_minute ?? null,
				interval_days: newSchedule.interval_days ?? 1,
				timezone: newSchedule.timezone ?? "UTC"
			}
		}
	},
	{ immediate: true }
)

async function fetchRepositories() {
	loadingRepositories.value = true
	try {
		const response = await Api.snapshots.getRepositories()
		if (response.data.success) {
			repositories.value = response.data.repositories
		}
	} catch (error: any) {
		message.error(error.message || "Failed to fetch repositories")
	} finally {
		loadingRepositories.value = false
	}
}

async function handleSubmit() {
	try {
		await formRef.value?.validate()
	} catch {
		return
	}

	loading.value = true
	try {
		let response
		if (isEditing.value && props.schedule) {
			response = await Api.snapshots.updateSchedule(props.schedule.id, formData.value)
		} else {
			response = await Api.snapshots.createSchedule(formData.value)
		}

		if (response.data.success) {
			emit("success")
		} else {
			message.error(response.data.message)
		}
	} catch (error: any) {
		message.error(error.message || "Failed to save schedule")
	} finally {
		loading.value = false
	}
}

onBeforeMount(() => {
	fetchRepositories()
})
</script>
