<template>
	<div class="flex w-full gap-3">
		<div v-if="userPic" class="pt-0.5">
			<n-avatar round :size="32" :src="userPic" />
		</div>
		<div class="flex grow flex-col gap-1 overflow-hidden">
			<div class="ml-0.5 flex items-center gap-3">
				<div class="font-semibold">
					{{ comment.user_name }}
				</div>
				<div class="text-secondary text-2xs font-mono">
					{{ formatDate(comment.created_at, dFormats.datetime) }}
				</div>
			</div>
			<div
				v-if="mode === 'view'"
				class="border-default rounded-lg border px-2.5 py-2 whitespace-pre-wrap"
				:class="embedded ? 'bg-secondary' : 'bg-default'"
			>
				{{ comment.comment }}
			</div>

			<n-input
				v-if="mode === 'edit'"
				v-model:value="commentModel"
				type="textarea"
				:disabled="saving"
				placeholder="Insert the updated comment"
				size="large"
				:autosize="{
					minRows: 3,
					maxRows: 18
				}"
			/>

			<div class="comment-actions flex justify-end gap-1">
				<template v-if="mode === 'view'">
					<n-button size="tiny" secondary :disabled="canceling" @click="editComment()">
						<template #icon>
							<Icon :name="EditIcon" :size="12" />
						</template>
						<span>Edit</span>
					</n-button>
					<n-popconfirm to="body" @positive-click="deleteCaseComment()">
						<template #trigger>
							<n-button size="tiny" secondary type="error" :loading="canceling">
								<template #icon>
									<Icon :name="DeleteIcon" :size="12" />
								</template>
								<span>Delete</span>
							</n-button>
						</template>
						Are you sure you want to delete the comment?
					</n-popconfirm>
				</template>
				<template v-if="mode === 'edit'">
					<n-button size="tiny" secondary :disabled="saving" @click="setMode('view')">
						<template #icon>
							<Icon :name="ArrowLeftIcon" :size="12" />
						</template>
						<span>Cancel</span>
					</n-button>

					<n-button
						size="tiny"
						secondary
						type="success"
						:loading="saving"
						:disabled="!commentModel"
						@click="updateCaseComment()"
					>
						<template #icon>
							<Icon :name="SaveIcon" :size="13" />
						</template>
						<span>Save</span>
					</n-button>
				</template>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CaseComment } from "@/types/incidentManagement/cases"
import { NAvatar, NButton, NInput, NPopconfirm, useMessage } from "naive-ui"
import { onBeforeMount, ref, toRefs } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"

import { getApiErrorMessage, getAvatar, getNameInitials } from "@/utils"
import { formatDate } from "@/utils/format"

type Mode = "view" | "edit"

const props = defineProps<{ comment: CaseComment; embedded?: boolean }>()

const emit = defineEmits<{
	(e: "deleted"): void
	(e: "updated", value: CaseComment): void
}>()

const { comment, embedded } = toRefs(props)

const ArrowLeftIcon = "carbon:arrow-left"
const SaveIcon = "carbon:save"
const EditIcon = "uil:edit-alt"
const DeleteIcon = "ph:trash"
const mode = ref<Mode>("view")
const canceling = ref(false)
const saving = ref(false)
const dFormats = useSettingsStore().dateFormat
const userPic = ref("")
const commentModel = ref(comment.value.comment)
const message = useMessage()

function setMode(newMode: Mode) {
	mode.value = newMode
}

function editComment() {
	setMode("edit")
	commentModel.value = comment.value.comment
}

function updateCaseComment() {
	saving.value = true

	Api.incidentManagement.cases
		.updateCaseComment({
			case_id: comment.value.case_id,
			comment_id: comment.value.id,
			comment: commentModel.value,
			created_at: new Date(),
			user_name: comment.value.user_name
		})
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Comment updated successfully")
				setMode("view")
				emit("updated", res.data.comment)
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			saving.value = false
		})
}

function deleteCaseComment() {
	canceling.value = true

	Api.incidentManagement.cases
		.deleteCaseComment(comment.value.id)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Comment deleted successfully")
				emit("deleted")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			canceling.value = false
		})
}

onBeforeMount(() => {
	const initials = getNameInitials(comment.value.user_name)
	userPic.value = getAvatar({ seed: initials, text: initials, size: 64 })
})
</script>
