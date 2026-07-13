<template>
	<div class="flex flex-col">
		<n-spin :show="loadingDelete || loadingDetails">
			<ExclusionRuleForm
				v-if="editing && resolvedEntity"
				:entity="resolvedEntity"
				:class="fullWidth ? 'p-0' : 'p-6'"
				@submitted="updateEntity($event)"
			>
				<template #additionalActions>
					<n-button @click="editing = false">Close</n-button>
				</template>
			</ExclusionRuleForm>
			<ExclusionRuleDetails v-else-if="resolvedEntity" :entity="resolvedEntity" :full-width />
		</n-spin>

		<div v-if="!editing && resolvedEntity" class="flex items-center justify-end gap-4" :class="fullWidth ? 'pt-4' : 'p-6'">
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
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { ExclusionRule } from "@/types/incidentManagement/exclusion-rules"
import { NButton, NSpin, useDialog, useMessage } from "naive-ui"
import { computed, h, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import ExclusionRuleDetails from "./ExclusionRuleDetails.vue"
import ExclusionRuleForm from "./ExclusionRuleForm.vue"

const { entity, exclusionId, fullWidth = false } = defineProps<{
	entity?: ExclusionRule
	exclusionId?: number
	fullWidth?: boolean
}>()

const emit = defineEmits<{
	(e: "loaded", value: ExclusionRule): void
	(e: "deleted"): void
	(e: "updated"): void
}>()

const DeleteIcon = "ph:trash"
const EditIcon = "uil:edit-alt"

const message = useMessage()
const dialog = useDialog()
const loadingDetails = ref(false)
const loadingDelete = ref(false)
const editing = ref(false)
const fetchedEntity = ref<ExclusionRule | undefined>(undefined)

const resolvedEntity = computed(() => entity ?? fetchedEntity.value)

function getDetails(id: number) {
	loadingDetails.value = true

	Api.incidentManagement.exclusionRules
		.getExclusionRule(id)
		.then(res => {
			if (res.data.success && res.data.exclusion_response) {
				fetchedEntity.value = res.data.exclusion_response
				emit("loaded", res.data.exclusion_response)
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingDetails.value = false
		})
}

function updateEntity(value: ExclusionRule) {
	if (resolvedEntity.value) {
		Object.assign(resolvedEntity.value, value)
	}
	editing.value = false
	emit("updated")
}

function deleteExclusionRule() {
	if (!resolvedEntity.value) return

	loadingDelete.value = true

	Api.incidentManagement.exclusionRules
		.deleteExclusionRules(resolvedEntity.value.id)
		.then(res => {
			if (res.data.success) {
				emit("deleted")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
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
				innerHTML: `Are you sure you want to delete the Exclusion Rule: <strong>${resolvedEntity.value?.name}</strong> ?`
			}),
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deleteExclusionRule()
		},
		onNegativeClick: () => {
			message.info("Delete canceled")
		}
	})
}

onBeforeMount(() => {
	if (entity) return
	if (exclusionId != null) getDetails(exclusionId)
})
</script>
