<template>
	<CardEntity size="small" embedded>
		<template #header-main>{{ comment.user_name }}</template>
		<template #header-extra>{{ formatDate(comment.created_at, dFormats.datetime) }}</template>
		<template #default>
			<n-input
				v-if="editMode"
				v-model:value="newComment"
				type="textarea"
				:autosize="{ minRows: 3, maxRows: 10 }"
			/>
			<div v-else class="whitespace-pre-wrap">{{ comment.comment }}</div>
		</template>
		<!-- The backend lets a portal user change only their own comments. -->
		<template v-if="isOwn && !readOnly" #footer-extra>
			<div v-if="editMode" class="flex items-center gap-2">
				<n-button
					size="tiny"
					type="primary"
					secondary
					:focusable="false"
					:disabled="!newComment?.trim()"
					:loading="updating"
					@click="updateComment"
				>
					<template #icon>
						<Icon name="carbon:save" />
					</template>
					{{ $t("common.actions.save") }}
				</n-button>
				<n-button size="tiny" :focusable="false" :disabled="updating" @click="setEditMode(false)">
					<template #icon>
						<Icon name="carbon:delete" />
					</template>
					{{ $t("common.actions.cancel") }}
				</n-button>
			</div>
			<div v-else class="flex items-center gap-2">
				<n-button size="tiny" :focusable="false" :disabled="deleting" @click="setEditMode(true)">
					<template #icon>
						<Icon name="carbon:edit" />
					</template>
					{{ $t("common.actions.edit") }}
				</n-button>

				<n-popconfirm to="body" @positive-click="deleteComment">
					<template #trigger>
						<n-button size="tiny" :focusable="false" :loading="deleting">
							<template #icon>
								<Icon name="carbon:trash-can" />
							</template>
							{{ $t("common.actions.delete") }}
						</n-button>
					</template>
					{{ $t("alerts.comments.confirmDelete") }}
				</n-popconfirm>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { CommentItem } from "@/types/comments"
import type { ApiError } from "@/types/common"
import { NButton, NInput, NPopconfirm, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import { useI18n } from "vue-i18n"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const { comment, alertId, readOnly } = defineProps<{
	comment: CommentItem
	alertId: number
	/** The user may only read this customer's data: no edit or delete (#1312). */
	readOnly?: boolean
}>()

const emit = defineEmits<{
	(e: "updated", comment: CommentItem): void
	(e: "deleted", commentId: number): void
}>()

const message = useMessage()
const { t } = useI18n()
const authStore = useAuthStore()
const dFormats = useSettingsStore().dateFormat
const editMode = ref(false)
const newComment = ref<string | null>(null)
const updating = ref(false)
const deleting = ref(false)
const isOwn = computed(() => !!authStore.userName && comment.user_name === authStore.userName)

function setEditMode(mode: boolean) {
	editMode.value = mode

	if (mode) {
		newComment.value = comment.comment
	}
}

async function updateComment() {
	if (!alert || !newComment.value?.trim()) return

	updating.value = true

	try {
		const response = await Api.alerts.updateComment({
			alertId,
			commentId: comment.id,
			comment: newComment.value.trim(),
			userName: authStore.userName || ""
		})

		emit("updated", response.data.comment)
		newComment.value = ""
		message.success(response.data?.message || t("alerts.comments.updated"))
		setEditMode(false)
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		updating.value = false
	}
}

async function deleteComment() {
	if (!comment) return

	deleting.value = true

	try {
		const response = await Api.alerts.deleteComment(comment.id)
		emit("deleted", comment.id)
		message.success(response.data?.message || t("alerts.comments.deleted"))
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		deleting.value = false
	}
}
</script>
