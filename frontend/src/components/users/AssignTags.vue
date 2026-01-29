<template>
	<div class="assign-tags-box flex flex-col gap-2 px-3 py-2">
		<div class="title flex items-center gap-2">
			<Icon :name="TagIcon" :size="16" />
			<span>Assign Tags</span>
		</div>

		<n-spin :show="loading" size="small">
			<div v-if="!tagRbacEnabled" class="text-xs opacity-70">
				Tag RBAC is disabled
			</div>

			<div v-else class="flex flex-col gap-2">
				<n-select
					v-model:value="selectedTagIds"
					multiple
					filterable
					clearable
					size="small"
					placeholder="No restrictions (full access)"
					:options="tagOptions"
					:loading="loadingTags"
					:disabled="saving"
				/>

				<div class="flex gap-2">
					<n-button
						size="small"
						type="primary"
						:loading="saving"
						:disabled="!hasChanges"
						@click="saveTags"
					>
						Save
					</n-button>
					<n-button
						v-if="selectedTagIds.length > 0"
						size="small"
						quaternary
						:disabled="saving"
						@click="clearAllTags"
					>
						Clear All
					</n-button>
				</div>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { AlertTag } from "@/types/incidentManagement/tags.d"
import type { User } from "@/types/user.d"
import { NButton, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, onMounted, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
    user: User | undefined
}>()

const emit = defineEmits<{
    (e: "success"): void
}>()

const TagIcon = "carbon:tag"

const message = useMessage()

const loading = ref(false)
const loadingTags = ref(false)
const saving = ref(false)
const tagRbacEnabled = ref(false)
const availableTags = ref<AlertTag[]>([])
const selectedTagIds = ref<number[]>([])
const originalTagIds = ref<number[]>([])

const tagOptions = computed(() =>
    availableTags.value.map(tag => ({
        label: tag.tag,
        value: tag.id
    }))
)

const hasChanges = computed(() => {
    if (selectedTagIds.value.length !== originalTagIds.value.length) return true
    const sorted1 = [...selectedTagIds.value].sort()
    const sorted2 = [...originalTagIds.value].sort()
    return sorted1.some((val, idx) => val !== sorted2[idx])
})

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

    loading.value = true
    try {
        const res = await Api.tagRbac.getUserTags(props.user.id)
        if (res.data.success) {
            // Backend returns accessible_tags, not tag_ids
            const tagIds = res.data.accessible_tags.map(tag => tag.id)
            selectedTagIds.value = tagIds
            originalTagIds.value = [...tagIds]
        }
    } catch (error) {
        console.error("Failed to load user tags:", error)
    } finally {
        loading.value = false
    }
}

async function saveTags() {
    if (!props.user?.id) return

    saving.value = true
    try {
        const res = await Api.tagRbac.assignUserTags(props.user.id, selectedTagIds.value)
        if (res.data.success) {
            message.success("Tag access updated")
            // Update original from response
            const tagIds = res.data.accessible_tags.map(tag => tag.id)
            originalTagIds.value = [...tagIds]
            emit("success")
        } else {
            message.error(res.data.message || "Failed to update tag access")
        }
    } catch (error: any) {
        message.error(error.response?.data?.message || "Failed to update tag access")
    } finally {
        saving.value = false
    }
}

async function clearAllTags() {
    if (!props.user?.id) return

    saving.value = true
    try {
        // Use assignUserTags with empty array to clear all
        const res = await Api.tagRbac.assignUserTags(props.user.id, [])
        if (res.data.success) {
            message.success("Tag restrictions cleared")
            selectedTagIds.value = []
            originalTagIds.value = []
            emit("success")
        }
    } catch (error: any) {
        message.error(error.response?.data?.message || "Failed to clear tags")
    } finally {
        saving.value = false
    }
}

watch(
    () => props.user?.id,
    () => {
        if (props.user?.id) {
            loadUserTags()
        }
    }
)

onMounted(async () => {
    await loadSettings()
    if (tagRbacEnabled.value) {
        await loadAvailableTags()
        if (props.user?.id) {
            await loadUserTags()
        }
    }
})
</script>

<style scoped lang="scss">
.assign-tags-box {
    min-width: 250px;

    .title {
        font-size: 14px;
        font-weight: 500;
    }
}
</style>
