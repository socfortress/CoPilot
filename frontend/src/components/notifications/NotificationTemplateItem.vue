<template>
	<CardEntity hoverable embedded footer-box-class="items-center!">
		<template #headerMain>
			<div class="flex items-center gap-2">
				<Icon :name="FormatIcon" :size="16" />
				<span class="font-medium">{{ template.name }}</span>
			</div>
		</template>

		<template #headerExtra>
			<Badge v-if="template.is_default" type="splitted" size="small">
				<template #label>built-in</template>
				<template #value>read-only</template>
			</Badge>
		</template>

		<template #default>
			<div class="flex flex-col gap-3 text-sm">
				<div v-if="template.description">{{ template.description }}</div>

				<!-- The first few lines, so the list is scannable without opening each one. -->
				<code class="text-secondary block overflow-hidden text-xs leading-relaxed whitespace-pre-wrap">
					{{ excerpt }}
				</code>

				<div class="flex flex-wrap items-center gap-2">
					<Badge type="splitted" size="small">
						<template #label>format</template>
						<template #value>{{ template.format }}</template>
					</Badge>
					<Badge type="splitted" size="small">
						<template #label>trigger</template>
						<template #value>{{ template.trigger ? triggerLabel : "any" }}</template>
					</Badge>
					<Badge type="splitted" size="small">
						<template #label>scope</template>
						<template #value>{{ template.customer_code ?? "all customers" }}</template>
					</Badge>
					<Badge v-if="template.subject_template" type="splitted" size="small">
						<template #label>subject</template>
						<template #value>set</template>
					</Badge>
				</div>
			</div>
		</template>

		<template #footerMain>
			<div class="flex flex-wrap items-center gap-2">
				<Badge v-if="template.created_by" type="splitted">
					<template #label>owner</template>
					<template #value>{{ template.created_by }}</template>
				</Badge>
				<Badge type="splitted">
					<template #label>updated</template>
					<template #value>
						{{ formatDate(template.updated_at ?? template.created_at, dFormats.datetime) }}
					</template>
				</Badge>
			</div>
		</template>

		<template #footerExtra>
			<div class="flex items-center justify-end gap-2">
				<!--
					Built-ins are read-only because the next startup would recreate
					them anyway. Duplicate is offered in their place: the copy is a
					normal row the operator owns.
				-->
				<n-button size="tiny" quaternary @click="$emit('duplicate')">
					<template #icon>
						<Icon :name="CopyIcon" :size="14" />
					</template>
					Duplicate
				</n-button>

				<n-button v-if="!template.is_default" size="tiny" quaternary @click="$emit('edit')">
					<template #icon>
						<Icon :name="EditIcon" :size="14" />
					</template>
					Edit
				</n-button>

				<n-popconfirm v-if="!template.is_default" to="body" @positive-click="confirmDelete">
					<template #trigger>
						<n-button size="tiny" quaternary :loading="loadingDelete">
							<template #icon>
								<Icon :name="DeleteIcon" :size="14" />
							</template>
							Delete
						</n-button>
					</template>
					Delete this template? Any route using it keeps working — it falls back to its own template or the
					channel default.
				</n-popconfirm>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { NotificationTemplate, NotificationTrigger } from "@/types/notifications"
import { NButton, NPopconfirm, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	template: NotificationTemplate
}>()

const emit = defineEmits<{
	(e: "edit"): void
	(e: "duplicate"): void
	(e: "deleted"): void
}>()

const FormatIcon = "carbon:document-blank"
const EditIcon = "uil:edit-alt"
const DeleteIcon = "ph:trash"
const CopyIcon = "carbon:copy"

const TRIGGER_LABELS: Record<NotificationTrigger, string> = {
	alert_created: "Alert created",
	investigation_complete: "AI investigation complete",
	alert_assigned: "Alert assigned",
	case_assigned: "Case assigned",
	case_task_assigned: "Case task assigned"
}

const message = useMessage()
const loadingDelete = ref(false)
const dFormats = useSettingsStore().dateFormat

const triggerLabel = computed(() =>
	props.template.trigger ? (TRIGGER_LABELS[props.template.trigger] ?? props.template.trigger) : "any"
)

const excerpt = computed(() => {
	const lines = props.template.body_template.split("\n").slice(0, 3)
	const truncated = props.template.body_template.split("\n").length > 3
	return lines.join("\n") + (truncated ? "\n…" : "")
})

function confirmDelete() {
	loadingDelete.value = true
	Api.notifications
		.deleteTemplate(props.template.id)
		.then(res => {
			// The message names how many routes were detached — worth surfacing,
			// since those routes just changed what they send.
			message.success(res.data.message || "Template deleted")
			emit("deleted")
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Could not delete the template")
		})
		.finally(() => {
			loadingDelete.value = false
		})
}
</script>
