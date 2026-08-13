<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-wrap items-end gap-3">
			<n-form-item label="Event source" :show-feedback="false" class="mb-0! min-w-60 grow">
				<n-select
					v-model:value="selectedEventSourceId"
					:options="eventSourceOptions"
					placeholder="Select the event source to enable dashboards against"
					clearable
				/>
			</n-form-item>

			<n-button type="primary" @click="openEditor(null)">
				<template #icon>
					<Icon :name="AddIcon" />
				</template>
				New dashboard
			</n-button>
		</div>

		<n-alert v-if="!eventSourceOptions.length" title="No enabled event sources" type="warning">
			You can still create and edit custom dashboards, but enabling one for this customer needs an enabled
			<strong>Event Source</strong>
			— it supplies the index pattern and time field the widgets query.
		</n-alert>

		<div class="flex items-center justify-between">
			<p class="text-secondary text-sm">Custom Dashboards</p>
			<span class="text-secondary text-sm">{{ customDashboards.length }} available</span>
		</div>

		<n-spin :show="loading">
			<div v-if="customDashboards.length" class="grid grid-cols-1 gap-3 @xl:grid-cols-2 @4xl:grid-cols-3">
				<CustomDashboardCard
					v-for="dashboard of customDashboards"
					:key="dashboard.template_key"
					:dashboard
					:selected-customer-code="customerCode"
					:selected-event-source-id
					:enabled-dashboards
					@edit="openEditor($event)"
					@deleted="fetchCustomDashboards()"
					@refresh-enabled-dashboards="emit('refreshEnabledDashboards')"
				/>
			</div>
			<n-empty
				v-else-if="!loading"
				description="No custom dashboards yet — create one, or load an exported definition"
				class="h-40 justify-center"
			/>
		</n-spin>

		<n-drawer
			v-model:show="showEditor"
			display-directive="if"
			:width="900"
			class="max-w-[92vw]"
			:trap-focus="false"
		>
			<n-drawer-content
				:title="editingDashboard ? `Edit ${editingDashboard.title}` : 'New custom dashboard'"
				closable
				:native-scrollbar="false"
			>
				<CustomDashboardEditor
					:key="editingDashboard?.template_key ?? 'new'"
					:customer-code
					:event-sources-list
					:editing="editingDashboard"
					@close="showEditor = false"
					@saved="onSaved()"
				/>
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CustomDashboard, EnabledDashboard } from "@/types/dashboards"
import type { EventSource } from "@/types/event-sources"
import { NAlert, NButton, NDrawer, NDrawerContent, NEmpty, NFormItem, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import CustomDashboardCard from "./CustomDashboardCard.vue"
import CustomDashboardEditor from "./CustomDashboardEditor.vue"

const { customerCode, eventSourcesList, enabledDashboards } = defineProps<{
	customerCode: string | null
	eventSourcesList: EventSource[]
	enabledDashboards: EnabledDashboard[]
}>()

const emit = defineEmits<{
	refreshEnabledDashboards: []
}>()

const AddIcon = "carbon:add"

const message = useMessage()

const loading = ref(false)
const customDashboards = ref<CustomDashboard[]>([])
const selectedEventSourceId = ref<number | null>(null)
const showEditor = ref(false)
const editingDashboard = ref<CustomDashboard | null>(null)

const eventSourceOptions = computed(() =>
	eventSourcesList
		.filter(source => source.enabled)
		.map(source => ({ label: `${source.name} (${source.event_type})`, value: source.id }))
)

function fetchCustomDashboards() {
	loading.value = true

	// The listing is scoped server-side: this customer's templates plus every
	// globally shared one.
	Api.siem
		.getCustomDashboards(customerCode)
		.then(res => {
			if (res.data.success) {
				customDashboards.value = res.data?.custom_dashboards || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

function openEditor(dashboard: CustomDashboard | null) {
	editingDashboard.value = dashboard
	showEditor.value = true
}

function onSaved() {
	showEditor.value = false
	fetchCustomDashboards()
}

watch(
	() => customerCode,
	() => {
		selectedEventSourceId.value = null
		fetchCustomDashboards()
	},
	{ immediate: true }
)

// Auto-select when the customer has exactly one source: enabling is then one click.
watch(
	eventSourceOptions,
	options => {
		if (!selectedEventSourceId.value && options.length === 1) {
			selectedEventSourceId.value = options[0].value
		}
	},
	{ immediate: true }
)

defineExpose({ refreshCustomDashboards: fetchCustomDashboards })
</script>
