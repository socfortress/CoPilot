<template>
	<CardEntity hoverable embedded>
		<template #headerMain>
			<div class="flex items-center gap-2">
				<Icon :name="channelIcon" :size="16" />
				<span class="font-medium">{{ route.name }}</span>
				<Badge v-if="!route.enabled" type="splitted" color="warning">
					<template #label>Status</template>
					<template #value>Disabled</template>
				</Badge>
			</div>
		</template>

		<template #headerExtra>
			<div class="flex items-center gap-2">
				<n-tooltip>
					<template #trigger>
						<n-button size="tiny" quaternary circle @click="toggleEnabled">
							<template #icon>
								<Icon :name="route.enabled ? PauseIcon : PlayIcon" :size="14" />
							</template>
						</n-button>
					</template>
					{{ route.enabled ? "Disable" : "Enable" }}
				</n-tooltip>

				<n-tooltip>
					<template #trigger>
						<n-button size="tiny" quaternary circle @click="$emit('edit')">
							<template #icon>
								<Icon :name="EditIcon" :size="14" />
							</template>
						</n-button>
					</template>
					Edit
				</n-tooltip>

				<n-popconfirm @positive-click="confirmDelete">
					<template #trigger>
						<n-button size="tiny" quaternary circle>
							<template #icon>
								<Icon :name="DeleteIcon" :size="14" />
							</template>
						</n-button>
					</template>
					Delete this route? Dispatch log entries will be retained.
				</n-popconfirm>
			</div>
		</template>

		<template #default>
			<div class="flex flex-col gap-2 text-sm">
				<div class="flex flex-wrap items-center gap-2">
					<Badge type="splitted" bright>
						<template #label>Trigger</template>
						<template #value>{{ triggerLabel }}</template>
					</Badge>
					<Badge type="splitted" :color="severityColor">
						<template #label>Min severity</template>
						<template #value>{{ route.min_severity }}</template>
					</Badge>
					<Badge type="splitted">
						<template #label>Channel</template>
						<template #value>{{ channelLabel }}</template>
					</Badge>
				</div>
				<div class="text-secondary">
					<span class="font-medium">Destination:</span>
					<code class="ml-1 break-all">{{ destinationDisplay }}</code>
				</div>
				<div v-if="route.format_template" class="text-secondary">
					<span class="font-medium">Custom template:</span>
					<span class="ml-1 italic">configured</span>
				</div>
			</div>
		</template>

		<template #footer>
			<div class="text-tertiary flex items-center gap-3 text-xs">
				<span>{{ route.dispatch_count }} dispatch(es)</span>
				<span>·</span>
				<span v-if="route.last_dispatched_at">
					last fired {{ formatDate(route.last_dispatched_at, "MMM D, YYYY HH:mm") }}
				</span>
				<span v-else>never fired</span>
				<span v-if="route.created_by">· created by {{ route.created_by }}</span>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { NotificationRoute } from "@/types/notifications.d"
import { NButton, NPopconfirm, NTooltip, useMessage } from "naive-ui"
import { computed } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	route: NotificationRoute
}>()

const emit = defineEmits<{
	(e: "edit"): void
	(e: "deleted"): void
	(e: "toggled"): void
}>()

const EditIcon = "carbon:edit"
const DeleteIcon = "carbon:trash-can"
const PauseIcon = "carbon:pause"
const PlayIcon = "carbon:play"

const message = useMessage()

// Phase 1 channels: SMTP only. Phase 2 will branch this on `shuffle`
// (and inspect the underlying integration's app to pick a Slack/Teams/
// Outlook icon respectively).
const channelIcon = computed(() => "carbon:email")
const channelLabel = computed(() => "SMTP email")

const triggerLabel = computed(() =>
	props.route.trigger === "investigation_complete"
		? "Every investigation"
		: "Critical / High only"
)

const severityColor = computed<"danger" | "warning" | "success">(() => {
	if (props.route.min_severity === "Critical" || props.route.min_severity === "High") return "danger"
	if (props.route.min_severity === "Medium") return "warning"
	return "success"
})

// SMTP recipients shown verbatim — email addresses aren't secrets the
// way Slack webhook URLs were. Phase 2 may reintroduce per-channel
// formatting logic for shuffle integrations.
const destinationDisplay = computed(() => props.route.destination)

async function toggleEnabled() {
	try {
		const res = await Api.notifications.updateRoute(
			props.route.customer_code,
			props.route.id,
			{ enabled: !props.route.enabled }
		)
		if (res.data.success) {
			message.success(`Route ${res.data.route.enabled ? "enabled" : "disabled"}`)
			emit("toggled")
		} else {
			message.warning(res.data.message || "Failed to toggle route")
		}
	} catch (err: unknown) {
		message.error(getApiErrorMessage(err as never) || "Failed to toggle route")
	}
}

async function confirmDelete() {
	try {
		const res = await Api.notifications.deleteRoute(props.route.customer_code, props.route.id)
		if (res.data.success) {
			message.success("Route deleted")
			emit("deleted")
		} else {
			message.warning(res.data.message || "Failed to delete route")
		}
	} catch (err: unknown) {
		message.error(getApiErrorMessage(err as never) || "Failed to delete route")
	}
}
</script>
