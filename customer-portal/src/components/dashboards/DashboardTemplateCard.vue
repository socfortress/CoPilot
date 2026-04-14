<template>
	<CardEntity hoverable size="small">
		<template #headerMain>
			{{ template.title }}
		</template>
		<template #default>
			<p class="text-xs">
				{{ template.description }}
			</p>
		</template>

		<template #footerMain>
			<Badge type="splitted">
				<template #label>Panels</template>
				<template #value>{{ template.panels.length }}</template>
			</Badge>
		</template>

		<template #footerExtra>
			<n-tooltip v-if="!isEnabled" :disabled="!disabledTooltipText" class="px-2! py-1!">
				<template #trigger>
					<n-button size="small" type="primary" :disabled="!canEnable" @click="onEnable">
						<template #icon>
							<Icon :name="disabledTooltipText ? LockedIcon : EnableIcon" />
						</template>
						Enable
					</n-button>
				</template>
				<div class="text-sm">
					{{ disabledTooltipText }}
				</div>
			</n-tooltip>
			<n-button v-else size="small" type="error" quaternary @click="onDisable">
				<template #icon>
					<Icon :name="DisableIcon" />
				</template>
				Disable
			</n-button>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { DashboardTemplate, EnabledDashboard } from "@/types/dashboards.d"
import { NButton, NTooltip, useDialog, useMessage } from "naive-ui"
import { computed } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	template: DashboardTemplate
	selectedCustomerCode: string | null
	selectedEventSourceId: number | null
	selectedCategoryId: string | null
	enabledDashboards: EnabledDashboard[]
	disabledTooltipText?: string
}>()

const emit = defineEmits<{
	refreshEnabledDashboards: []
}>()

const message = useMessage()
const dialog = useDialog()

const EnableIcon = "carbon:add-alt"
const DisableIcon = "carbon:subtract-alt"
const LockedIcon = "carbon:locked"

const canEnable = computed(() => !!props.selectedCustomerCode && !!props.selectedEventSourceId)

const isEnabled = computed(() => {
	if (!props.selectedCategoryId || !props.selectedEventSourceId) return false

	return props.enabledDashboards.some(
		d =>
			d.library_card === props.selectedCategoryId &&
			d.template_id === props.template.id &&
			d.event_source_id === props.selectedEventSourceId
	)
})

function onEnable() {
	if (!props.selectedCustomerCode || !props.selectedEventSourceId || !props.selectedCategoryId) {
		message.warning("Please select a customer and event source first")
		return
	}

	Api.siem
		.enableDashboard({
			customer_code: props.selectedCustomerCode,
			event_source_id: props.selectedEventSourceId,
			library_card: props.selectedCategoryId,
			template_id: props.template.id,
			display_name: props.template.title
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
}

function onDisable() {
	const match = props.enabledDashboards.find(
		d =>
			d.library_card === props.selectedCategoryId &&
			d.template_id === props.template.id &&
			d.event_source_id === props.selectedEventSourceId
	)

	if (!match) return

	dialog.warning({
		title: "Disable Dashboard",
		content: `Are you sure you want to disable "${props.template.title}"?`,
		positiveText: "Disable",
		negativeText: "Cancel",
		onPositiveClick: () => {
			Api.siem
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
		}
	})
}
</script>
