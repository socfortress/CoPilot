<template>
	<n-spin :show="deletingTag" size="small" content-class="flex flex-wrap gap-2">
		<n-tag v-for="tag of alert.tags" :key="tag.id" closable size="small" @close="deleteTag(tag.id)">
			{{ tag.tag }}
		</n-tag>

		<n-dynamic-tags size="small" :value="[]" @create="newAlertTag">
			<template #trigger="{ activate, disabled }">
				<n-button
					size="tiny"
					type="primary"
					dashed
					:loading="creatingTag"
					:disabled="disabled"
					@click="activate()"
				>
					<template #icon>
						<Icon :name="AddIcon" />
					</template>
					New Tag
				</n-button>
			</template>
		</n-dynamic-tags>
	</n-spin>
</template>

<script setup lang="ts">
import type { Alert } from "@/types/incidentManagement/alerts.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import _trim from "lodash/trim"
import { NButton, NDynamicTags, NSpin, NTag, useMessage } from "naive-ui"
import { ref, toRefs } from "vue"

const props = defineProps<{ alert: Alert }>()
const emit = defineEmits<{
	(e: "updated", value: Alert): void
}>()

const { alert } = toRefs(props)

const AddIcon = "carbon:add"

const message = useMessage()
const creatingTag = ref(false)
const deletingTag = ref(false)

function updateAlert(updatedAlert: Alert) {
	emit("updated", updatedAlert)
}

function deleteTag(tagId: number) {
	deletingTag.value = true

	Api.incidentManagement
		.deleteAlertTag(alert.value.id, tagId)
		.then(res => {
			if (res.data.success) {
				alert.value.tags = alert.value.tags.filter(o => o.id !== tagId)
				updateAlert(alert.value)
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (err.response?.status === 401) {
				message.error(err.response?.data?.message || "Alert tag Delete returned Unauthorized.")
			} else {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			deletingTag.value = false
		})
}

function newAlertTag(text: string): string | { label: string, value: string } {
	const tag = _trim(text)

	if (tag && alert.value.tags.filter(o => o.tag.toLowerCase() === tag.toLowerCase()).length === 0) {
		creatingTag.value = true

		Api.incidentManagement
			.newAlertTag(alert.value.id, tag)
			.then(res => {
				if (res.data.success) {
					alert.value.tags.push(res.data.alert_tag)
					updateAlert(alert.value)
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				creatingTag.value = false
			})
	}

	return ""
}
</script>
