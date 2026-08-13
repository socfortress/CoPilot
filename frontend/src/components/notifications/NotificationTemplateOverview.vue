<template>
	<div class="flex flex-col">
		<n-spin :show="loadingDelete || loadingDetails">
			<div v-if="editing && resolvedEntity" class="flex flex-col gap-4" :class="fullWidth ? 'p-0' : 'p-6'">
				<NotificationTemplateForm
					:editing-template="resolvedEntity"
					@submitted="updateEntity($event)"
					@close="editing = false"
				/>
			</div>
			<NotificationTemplateDetails v-else-if="resolvedEntity" :entity="resolvedEntity" :full-width />
			<div v-else-if="!loadingDetails" class="min-h-40"></div>
		</n-spin>

		<div
			v-if="!editing && resolvedEntity"
			class="flex flex-wrap items-center justify-end gap-4"
			:class="fullWidth ? 'pt-4' : 'p-6'"
		>
			<!--
				Built-ins are read-only because the next startup would recreate them
				anyway. Duplicate is offered in their place: the copy is a normal row
				the operator owns.
			-->
			<n-button v-if="resolvedEntity.is_default" @click="emit('duplicate', resolvedEntity)">
				<template #icon>
					<Icon :name="CopyIcon" :size="14" />
				</template>
				Duplicate
			</n-button>

			<template v-else>
				<n-button text type="error" ghost :loading="loadingDelete" @click="handleDelete">
					<template #icon>
						<Icon :name="DeleteIcon" :size="15" />
					</template>
					Delete
				</n-button>
				<n-button :disabled="loadingDelete" @click="editing = true">
					<template #icon>
						<Icon :name="EditIcon" :size="14" />
					</template>
					Edit
				</n-button>
			</template>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { NotificationTemplate } from "@/types/notifications"
import { NButton, NSpin, useDialog, useMessage } from "naive-ui"
import { h, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"
import { getApiErrorMessage } from "@/utils"
import NotificationTemplateDetails from "./NotificationTemplateDetails.vue"
import NotificationTemplateForm from "./NotificationTemplateForm.vue"

// Mounted both inside the list (the row already holds the template) and on the
// template's own route, where only the id is known — `useEntityDetails` owns
// that split so this component only supplies the fetcher.

const {
	entity,
	templateId,
	fullWidth = false
} = defineProps<{
	entity?: NotificationTemplate
	templateId?: number
	fullWidth?: boolean
}>()

const emit = defineEmits<{
	(e: "loaded", value: NotificationTemplate): void
	(e: "deleted"): void
	(e: "updated"): void
	(e: "duplicate", value: NotificationTemplate): void
}>()

const DeleteIcon = "ph:trash"
const EditIcon = "uil:edit-alt"
const CopyIcon = "carbon:copy"

const message = useMessage()
const dialog = useDialog()
const loadingDelete = ref(false)
const editing = ref(false)

const { loading: loadingDetails, entity: resolvedEntity } = useEntityDetails<NotificationTemplate, number>({
	entity: () => entity,
	id: () => templateId,
	fetch: id =>
		Api.notifications.getTemplate(id).then(res => ({
			entity: res.data.success ? (res.data.template ?? null) : null,
			message: res.data.message
		})),
	notFoundMessage: "Template not found.",
	errorMessage: "Could not load the template.",
	onLoaded: value => emit("loaded", value)
})

function updateEntity(value: NotificationTemplate) {
	if (resolvedEntity.value) {
		Object.assign(resolvedEntity.value, value)
	}
	editing.value = false
	emit("updated")
}

function deleteTemplate() {
	if (!resolvedEntity.value) return

	loadingDelete.value = true

	Api.notifications
		.deleteTemplate(resolvedEntity.value.id)
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

function handleDelete() {
	if (!resolvedEntity.value) return

	dialog.warning({
		title: "Confirm",
		content: () =>
			h("div", {
				innerHTML:
					`Delete the template <strong>${resolvedEntity.value?.name}</strong>? ` +
					`Any route using it keeps working — it falls back to its own template or the channel default.`
			}),
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deleteTemplate()
		},
		onNegativeClick: () => {
			message.info("Delete canceled")
		}
	})
}
</script>
