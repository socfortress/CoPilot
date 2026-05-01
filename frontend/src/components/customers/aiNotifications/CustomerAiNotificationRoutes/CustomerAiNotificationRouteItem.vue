<template>
	<CardEntity hoverable embedded>
		<template #headerMain>
			<div class="flex items-center gap-2">
				<Icon :name="channelIcon" :size="16" />
				<span class="font-medium">{{ route.name }}</span>
			</div>
		</template>

		<template #headerExtra>
			<n-button
				size="small"
				secondary
				:type="route.enabled ? 'warning' : 'success'"
				:loading="loadingToggle"
				@click="toggleEnabled"
			>
				<template #icon>
					<Icon :name="route.enabled ? PauseIcon : PlayIcon" />
				</template>
				{{ route.enabled ? "Disable" : "Enable" }}
			</n-button>
		</template>

		<template #default>
			<div class="flex flex-col gap-3 text-sm">
				<div class="flex flex-col gap-0.5 text-sm">
					<div class="flex flex-wrap gap-1">
						<span class="font-medium">Destination:</span>
						<span class="flex flex-wrap gap-1">
							<code v-for="destination in destinationList" :key="destination">{{ destination }}</code>
						</span>
					</div>
					<div v-if="route.format_template" class="flex flex-wrap gap-1">
						<span class="font-medium">Custom template:</span>
						<span class="italic">configured</span>
					</div>
				</div>
				<div class="flex flex-wrap items-center gap-2">
					<Badge type="splitted" :color="severityColor" size="small">
						<template #label>Min severity</template>
						<template #value>{{ route.min_severity }}</template>
					</Badge>
					<Badge type="splitted" size="small">
						<template #label>Channel</template>
						<template #value>{{ channelLabel }}</template>
					</Badge>
				</div>
			</div>
		</template>

		<template #footerMain>
			<div class="flex flex-wrap items-center gap-2">
				<Badge type="splitted">
					<template #label>dispatch</template>
					<template #value>{{ route.dispatch_count }}</template>
				</Badge>

				<Badge type="splitted">
					<template #label>fired</template>
					<template v-if="route.last_dispatched_at" #value>
						{{ formatDate(route.last_dispatched_at, dFormats.datetime) }}
					</template>
					<template v-else #value>never fired</template>
				</Badge>

				<Badge v-if="route.created_by" type="splitted">
					<template #label>owner</template>
					<template #value>{{ route.created_by }}</template>
				</Badge>
			</div>
		</template>

		<template #footerExtra>
			<div class="flex items-center justify-end gap-2">
				<n-button size="tiny" quaternary @click="$emit('edit')">
					<template #icon>
						<Icon :name="EditIcon" :size="14" />
					</template>
					Edit
				</n-button>

				<n-popconfirm to="body" @positive-click="confirmDelete">
					<template #trigger>
						<n-button size="tiny" quaternary :loading="loadingDelete">
							<template #icon>
								<Icon :name="DeleteIcon" :size="14" />
							</template>
							Delete
						</n-button>
					</template>
					Delete this route? Dispatch log entries will be retained.
				</n-popconfirm>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { NotificationRoute } from "@/types/notifications.d"
import _split from "lodash/split"
import { NButton, NPopconfirm, NTooltip, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
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

const loadingToggle = ref(false)
const loadingDelete = ref(false)
const message = useMessage()
const dFormats = useSettingsStore().dateFormat

// Channel icon + label. Shuffle routes show the underlying app name
// (cached on the route row at form-submit time, so we don't have to
// roundtrip to Shuffle on every list render).
const channelIcon = computed(() => {
	if (props.route.channel === "shuffle") return "carbon:integration"
	return "carbon:email"
})

const channelLabel = computed(() => {
	if (props.route.channel === "shuffle") {
		return props.route.shuffle_app_name ? `Shuffle · ${props.route.shuffle_app_name}` : "Shuffle"
	}
	return "SMTP email"
})

const severityColor = computed<"danger" | "warning" | "success">(() => {
	if (props.route.min_severity === "Critical" || props.route.min_severity === "High") return "danger"
	if (props.route.min_severity === "Medium") return "warning"
	return "success"
})

// SMTP recipients shown verbatim — email addresses aren't secrets the
// way Slack webhook URLs were. Phase 2 may reintroduce per-channel
// formatting logic for shuffle integrations.
const destinationList = computed(() => _split(props.route.destination, ","))

async function toggleEnabled() {
	loadingToggle.value = true

	try {
		const res = await Api.notifications.updateRoute(props.route.customer_code, props.route.id, {
			enabled: !props.route.enabled
		})
		if (res.data.success) {
			message.success(`Route ${res.data.route.enabled ? "enabled" : "disabled"}`)
			emit("toggled")
		} else {
			message.warning(res.data.message || "Failed to toggle route")
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to toggle route")
	} finally {
		loadingToggle.value = false
	}
}

async function confirmDelete() {
	loadingDelete.value = true

	try {
		const res = await Api.notifications.deleteRoute(props.route.customer_code, props.route.id)
		if (res.data.success) {
			message.success("Route deleted")
			emit("deleted")
		} else {
			message.warning(res.data.message || "Failed to delete route")
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to delete route")
	} finally {
		loadingDelete.value = false
	}
}
</script>
