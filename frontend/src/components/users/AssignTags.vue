<template>
	<div class="flex flex-col gap-0.5">
		<n-button quaternary class="w-full! justify-start!" @click="showModal = true">
			<template #icon>
				<Icon :name="TagIcon" :size="14" />
			</template>
			<div class="flex flex-col items-start gap-0.5">
				<span>Assign Tags</span>
				<n-spin :show="loadingPreview" size="small">
					<div v-if="!tagRbacEnabled" class="text-secondary text-xs">Tag RBAC is disabled</div>
					<div v-else-if="accessibleTags.length > 0" class="flex flex-wrap gap-1">
						<n-tag v-for="tag in accessibleTags" :key="tag.id" type="info" size="tiny">
							{{ tag.tag }}
						</n-tag>
					</div>
					<div v-else class="text-secondary text-xs">No restrictions (full access)</div>
				</n-spin>
			</div>
		</n-button>

		<n-modal
			v-model:show="showModal"
			display-directive="show"
			preset="card"
			:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(300px, 60vh)' }"
			title="Assign Tag Access"
			:bordered="false"
			content-class="flex flex-col"
			segmented
		>
			<div class="flex flex-col gap-4">
				<div>
					<strong>User:</strong>
					{{ user?.username }}
				</div>

				<template v-if="tagRbacEnabled">
					<n-form :model="formModel">
						<n-form-item label="Select Tags">
							<n-select
								v-model:value="formModel.tagIds"
								multiple
								filterable
								clearable
								placeholder="No restrictions (full access)"
								:options="tagOptions"
								:loading="loadingTags"
								:disabled="saving"
							/>
						</n-form-item>

						<n-form-item label="Current Access">
							<div v-if="accessibleTags.length > 0" class="flex flex-wrap gap-2">
								<n-tag v-for="tag in accessibleTags" :key="tag.id" type="info" size="small">
									{{ tag.tag }}
								</n-tag>
							</div>
							<div v-else class="text-secondary">No restrictions (full access)</div>
						</n-form-item>
					</n-form>

					<div class="flex justify-end gap-3">
						<n-button @click="showModal = false">Cancel</n-button>
						<n-button type="primary" :loading="saving" :disabled="!hasChanges" @click="saveTags">
							Save
						</n-button>
					</div>
				</template>

				<div v-else class="text-secondary">Tag RBAC is disabled</div>
			</div>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { AlertTag } from "@/types/tags"
import type { User } from "@/types/user"
import { NButton, NForm, NFormItem, NModal, NSelect, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	user?: User
}>()

const emit = defineEmits<{
	success: []
}>()

const TagIcon = "carbon:tag"

const message = useMessage()

const showModal = ref(false)
const loadingPreview = ref(false)
const loadingTags = ref(false)
const saving = ref(false)
const tagRbacEnabled = ref(false)
const availableTags = ref<AlertTag[]>([])
const accessibleTags = ref<AlertTag[]>([])

const formModel = ref({
	tagIds: [] as number[]
})

const tagOptions = computed(() =>
	availableTags.value.map((tag: AlertTag) => ({
		label: tag.tag,
		value: tag.id
	}))
)

const savedTagIds = computed(() => accessibleTags.value.map(tag => tag.id))

const hasChanges = computed(() => {
	if (formModel.value.tagIds.length !== savedTagIds.value.length) return true
	const sorted1 = formModel.value.tagIds.toSorted()
	const sorted2 = savedTagIds.value.toSorted()
	return sorted1.some((val, idx) => val !== sorted2[idx])
})

function syncFormFromAccess() {
	formModel.value.tagIds = accessibleTags.value.map(tag => tag.id)
}

async function loadSettings() {
	try {
		const res = await Api.tagRbac.getSettings()
		if (res.data.success && res.data.settings) {
			tagRbacEnabled.value = res.data.settings.enabled
		}
	} catch (error) {
		console.error("Failed to load tag RBAC settings:", error)
	}
}

async function loadAvailableTags() {
	loadingTags.value = true
	try {
		const res = await Api.tagRbac.getAvailableTags()
		if (res.data.success) {
			availableTags.value = res.data.tags
		}
	} catch (error) {
		console.error("Failed to load available tags:", error)
	} finally {
		loadingTags.value = false
	}
}

async function loadUserTags() {
	if (!props.user?.id) return

	loadingPreview.value = true
	try {
		const res = await Api.tagRbac.getUserTags(props.user.id)
		if (res.data.success) {
			accessibleTags.value = res.data.accessible_tags
		}
	} catch (error) {
		console.error("Failed to load user tags:", error)
	} finally {
		loadingPreview.value = false
	}
}

async function saveTags() {
	if (!props.user?.id) return

	saving.value = true
	try {
		const res = await Api.tagRbac.assignUserTags(props.user.id, formModel.value.tagIds)
		if (res.data.success) {
			message.success("Tag access updated")
			accessibleTags.value = res.data.accessible_tags
			showModal.value = false
			emit("success")
		} else {
			message.error(res.data.message || "Failed to update tag access")
		}
	} catch (error) {
		message.error(getApiErrorMessage(error as ApiError) || "Failed to update tag access")
	} finally {
		saving.value = false
	}
}

watch(showModal, newVal => {
	if (newVal && tagRbacEnabled.value) {
		loadAvailableTags()
		loadUserTags().then(syncFormFromAccess)
	}
})

// This instance is reused across table rows, so the bound user can change while
// mounted. Reload that user's tags if it changes while the modal is open, and
// clear stale state otherwise so a previous user's data is never shown.
watch(
	() => props.user?.id,
	async () => {
		if (showModal.value) {
			await loadUserTags()
			syncFormFromAccess()
		} else {
			formModel.value.tagIds = []
			if (props.user?.id && tagRbacEnabled.value) {
				await loadUserTags()
			} else {
				accessibleTags.value = []
			}
		}
	}
)

onBeforeMount(async () => {
	await loadSettings()
	if (tagRbacEnabled.value && props.user?.id) {
		await loadUserTags()
	}
})
</script>
