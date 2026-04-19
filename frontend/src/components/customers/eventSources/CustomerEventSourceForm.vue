<template>
	<div class="flex min-h-120 flex-col gap-4 overflow-hidden">
		<div class="flex flex-col gap-4 px-7 pt-4">
			<div class="text-sm font-semibold">{{ isEditing ? "Edit Event Source" : "New Event Source" }}</div>

			<n-form-item label="Name" required>
				<n-input v-model:value="form.name" placeholder="e.g. Wazuh Alerts" clearable />
			</n-form-item>

			<n-form-item label="Index Pattern" required>
				<n-input
					v-model:value="form.index_pattern"
					:placeholder="`e.g. wazuh-${props.customerCode}_*`"
					clearable
				/>
			</n-form-item>

			<n-form-item label="Event Type" required>
				<n-select v-model:value="form.event_type" :options="eventTypeOptions" placeholder="Select type" />
			</n-form-item>

			<n-form-item label="Time Field">
				<n-input v-model:value="form.time_field" placeholder="e.g. timestamp" clearable />
			</n-form-item>

			<n-form-item label="Enabled">
				<n-switch v-model:value="form.enabled" />
			</n-form-item>
		</div>

		<div class="flex justify-between gap-4 px-7 pb-4">
			<n-button @click="close()">Close</n-button>
			<n-button type="primary" :disabled="!isValid" :loading @click="submit()">
				{{ isEditing ? "Update" : "Create" }}
			</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { EventSource } from "@/types/eventSources.d"
import { NButton, NFormItem, NInput, NSelect, NSwitch, useMessage } from "naive-ui"
import { computed, reactive, ref } from "vue"
import Api from "@/api"

const props = defineProps<{
	customerCode: string
	editingSource?: EventSource | null
}>()

const emit = defineEmits<{
	(e: "close"): void
	(e: "submitted"): void
}>()

const message = useMessage()
const loading = ref(false)

const isEditing = computed(() => !!props.editingSource)

const eventTypeOptions = [
	{ label: "EDR", value: "EDR" },
	{ label: "EPP", value: "EPP" },
	{ label: "Cloud Integration", value: "Cloud Integration" },
	{ label: "Network Security", value: "Network Security" }
]

const form = reactive({
	name: props.editingSource?.name || "",
	index_pattern: props.editingSource?.index_pattern || "",
	event_type: props.editingSource?.event_type || (null as string | null),
	time_field: props.editingSource?.time_field || "timestamp",
	enabled: props.editingSource?.enabled ?? true
})

const isValid = computed(() => {
	return !!form.name && !!form.index_pattern && !!form.event_type
})

function submit() {
	if (!isValid.value) return

	loading.value = true

	if (isEditing.value && props.editingSource) {
		Api.siem
			.updateEventSource(props.editingSource.id, {
				name: form.name,
				index_pattern: form.index_pattern,
				event_type: form.event_type || "",
				time_field: form.time_field,
				enabled: form.enabled
			})
			.then(res => {
				if (res.data.success) {
					emit("submitted")
					message.success(res.data?.message || "Event source updated successfully.")
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				loading.value = false
			})
	} else {
		Api.siem
			.createEventSource({
				customer_code: props.customerCode,
				name: form.name,
				index_pattern: form.index_pattern,
				event_type: form.event_type || "",
				time_field: form.time_field,
				enabled: form.enabled
			})
			.then(res => {
				if (res.data.success) {
					emit("submitted")
					message.success(res.data?.message || "Event source created successfully.")
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				loading.value = false
			})
	}
}

function close() {
	emit("close")
}
</script>
