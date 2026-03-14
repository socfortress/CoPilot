<template>
	<div>
		<CardEntity hoverable :embedded>
			<template #default>
				<div class="flex items-center gap-3">
					<Icon :name="SourceIcon" :size="18" />
					<span class="font-semibold">{{ source.name }}</span>
				</div>
			</template>

			<template #footerMain>
				<div class="flex flex-wrap items-center gap-3">
					<Badge type="splitted" color="primary">
						<template #iconLeft>
							<Icon :name="TypeIcon" :size="13" />
						</template>
						<template #label>Type</template>
						<template #value>{{ source.event_type }}</template>
					</Badge>

					<Badge type="splitted" color="primary">
						<template #iconLeft>
							<Icon :name="IndexIcon" :size="13" />
						</template>
						<template #label>Index</template>
						<template #value>{{ source.index_pattern }}</template>
					</Badge>

					<Badge type="splitted" color="primary">
						<template #iconLeft>
							<Icon :name="TimeIcon" :size="13" />
						</template>
						<template #label>Time Field</template>
						<template #value>{{ source.time_field }}</template>
					</Badge>

					<Badge type="splitted" :color="source.enabled ? 'success' : 'danger'" bright>
						<template #iconLeft>
							<Icon :name="StatusIcon" :size="13" />
						</template>
						<template #value>{{ source.enabled ? "Enabled" : "Disabled" }}</template>
					</Badge>
				</div>
			</template>

			<template #footerExtra>
				<div class="flex flex-wrap gap-3">
					<n-button size="small" @click.stop="emit('edit')">
						<template #icon>
							<Icon :name="EditIcon" />
						</template>
						Edit
					</n-button>
					<n-button size="small" type="error" ghost :loading="loadingDelete" @click.stop="handleDelete">
						<template #icon>
							<Icon :name="DeleteIcon" :size="15" />
						</template>
						Delete
					</n-button>
				</div>
			</template>
		</CardEntity>
	</div>
</template>

<script setup lang="ts">
import type { EventSource } from "@/types/eventSources.d"
import { NButton, useDialog, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"

const { source, embedded } = defineProps<{
	source: EventSource
	embedded?: boolean
}>()

const emit = defineEmits<{
	(e: "edit"): void
	(e: "deleted"): void
}>()

const SourceIcon = "carbon:data-base"
const TypeIcon = "carbon:category"
const IndexIcon = "carbon:catalog"
const TimeIcon = "carbon:time"
const StatusIcon = "carbon:circle-dash"
const EditIcon = "carbon:edit"
const DeleteIcon = "ph:trash"

const dialog = useDialog()
const message = useMessage()
const loadingDelete = ref(false)

function handleDelete() {
	dialog.warning({
		title: "Delete Event Source",
		content: `Are you sure you want to delete the event source "${source.name}"?`,
		positiveText: "Delete",
		negativeText: "Cancel",
		onPositiveClick: () => {
			loadingDelete.value = true

			Api.siem
				.deleteEventSource(source.id)
				.then(res => {
					if (res.data.success) {
						emit("deleted")
						message.success(res.data?.message || "Event source deleted successfully.")
					} else {
						message.warning(res.data?.message || "An error occurred. Please try again later.")
					}
				})
				.catch(err => {
					message.error(err.response?.data?.message || "An error occurred. Please try again later.")
				})
				.finally(() => {
					loadingDelete.value = false
				})
		}
	})
}
</script>
