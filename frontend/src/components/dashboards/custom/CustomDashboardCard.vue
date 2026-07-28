<template>
	<CardEntity hoverable size="small">
		<template #headerMain>
			<div class="flex items-center gap-2">
				<div class="flex h-full items-center justify-center" :style="{ color: dashboard.color }">
					<Icon :name="getDashboardIcon(dashboard.icon)" :size="16" />
				</div>
				<span class="text-default">{{ dashboard.title }}</span>
			</div>
		</template>

		<template #headerExtra>
			<Badge v-if="dashboard.customer_code" type="splitted">
				<template #label>Scope</template>
				<template #value>#{{ dashboard.customer_code }}</template>
			</Badge>
			<Badge v-else type="active">
				<template #label>Shared with all customers</template>
			</Badge>
		</template>

		<template #default>
			<div class="flex flex-col gap-2">
				<p class="text-xs">{{ dashboard.description || "No description" }}</p>
				<div v-if="dashboard.tags?.length" class="text-tertiary flex flex-wrap gap-2 text-xs">
					<span v-for="tag of dashboard.tags" :key="tag">#{{ tag }}</span>
				</div>
			</div>
		</template>

		<template #footerMain>
			<div class="flex flex-wrap gap-2">
				<Badge type="splitted">
					<template #label>Widgets</template>
					<template #value>{{ dashboard.panels.length }}</template>
				</Badge>
				<Badge type="splitted">
					<template #label>Vendor</template>
					<template #value>{{ dashboard.vendor }}</template>
				</Badge>
			</div>
		</template>

		<template #footerExtra>
			<div class="flex flex-wrap items-center gap-1">
				<n-button size="small" quaternary @click="emit('edit', dashboard)">
					<template #icon>
						<Icon :name="EditIcon" />
					</template>
					Edit
				</n-button>

				<n-button size="small" quaternary type="error" :loading="deleting" @click="onDelete()">
					<template #icon>
						<Icon :name="DeleteIcon" />
					</template>
					Delete
				</n-button>

				<n-button v-if="isEnabled" size="small" type="error" quaternary :loading="toggling" @click="onDisable()">
					<template #icon>
						<Icon :name="DisableIcon" />
					</template>
					Disable
				</n-button>
				<n-tooltip v-else :disabled="canEnable">
					<template #trigger>
						<n-button
							size="small"
							type="primary"
							:disabled="!canEnable || toggling"
							:loading="toggling"
							@click="onEnable()"
						>
							<template #icon>
								<Icon :name="canEnable ? EnableIcon : LockedIcon" />
							</template>
							Enable
						</n-button>
					</template>
					Select an event source first
				</n-tooltip>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CustomDashboard, EnabledDashboard } from "@/types/dashboards"
import { NButton, NTooltip, useDialog, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { CUSTOM_LIBRARY_CARD } from "@/types/dashboards"
import { getApiErrorMessage } from "@/utils"
import { getDashboardIcon } from "../utils"

const { dashboard, selectedCustomerCode, selectedEventSourceId, enabledDashboards } = defineProps<{
	dashboard: CustomDashboard
	selectedCustomerCode: string | null
	selectedEventSourceId: number | null
	enabledDashboards: EnabledDashboard[]
}>()

const emit = defineEmits<{
	edit: [dashboard: CustomDashboard]
	refreshEnabledDashboards: []
	deleted: []
}>()

const EnableIcon = "carbon:add-alt"
const DisableIcon = "carbon:subtract-alt"
const LockedIcon = "carbon:locked"
const EditIcon = "carbon:edit"
const DeleteIcon = "carbon:trash-can"

const message = useMessage()
const dialog = useDialog()

const toggling = ref(false)
const deleting = ref(false)

const canEnable = computed(() => !!selectedCustomerCode && !!selectedEventSourceId)

const enabledEntry = computed(() =>
	enabledDashboards.find(
		item =>
			item.library_card === CUSTOM_LIBRARY_CARD &&
			item.template_id === dashboard.template_key &&
			item.event_source_id === selectedEventSourceId
	)
)

const isEnabled = computed(() => !!enabledEntry.value)

function onEnable() {
	if (!selectedCustomerCode || !selectedEventSourceId) return

	toggling.value = true

	Api.siem
		.enableDashboard({
			customer_code: selectedCustomerCode,
			event_source_id: selectedEventSourceId,
			library_card: CUSTOM_LIBRARY_CARD,
			template_id: dashboard.template_key,
			display_name: dashboard.title
		})
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Dashboard enabled successfully")
				emit("refreshEnabledDashboards")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			toggling.value = false
		})
}

function onDisable() {
	const match = enabledEntry.value
	if (!match) return

	dialog.warning({
		title: "Disable Dashboard",
		content: `Are you sure you want to disable "${dashboard.title}"?`,
		positiveText: "Disable",
		negativeText: "Cancel",
		onPositiveClick: () => {
			toggling.value = true

			return Api.siem
				.disableDashboard(match.id)
				.then(res => {
					if (res.data.success) {
						message.success(res.data?.message || "Dashboard disabled successfully")
						emit("refreshEnabledDashboards")
					} else {
						message.warning(res.data?.message || "An error occurred. Please try again later.")
					}
				})
				.catch(err => {
					message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
				})
				.finally(() => {
					toggling.value = false
				})
		}
	})
}

function onDelete() {
	dialog.warning({
		title: "Delete Custom Dashboard",
		content: `"${dashboard.title}" will be deleted, together with every dashboard enabled from it. Continue?`,
		positiveText: "Delete",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deleting.value = true

			return Api.siem
				.deleteCustomDashboard(dashboard.template_key)
				.then(res => {
					if (res.data.success) {
						message.success(res.data?.message || "Custom dashboard deleted successfully")
						emit("deleted")
						emit("refreshEnabledDashboards")
					} else {
						message.warning(res.data?.message || "An error occurred. Please try again later.")
					}
				})
				.catch(err => {
					message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
				})
				.finally(() => {
					deleting.value = false
				})
		}
	})
}
</script>
