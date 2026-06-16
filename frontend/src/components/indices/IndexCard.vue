<template>
	<CardEntity size="small" embedded :loading :status="healthStatus" header-box-class="flex-nowrap! items-start">
		<template #headerMain>
			<span class="text-default truncate font-mono text-sm font-semibold" :title="index.index">
				{{ index.index }}
			</span>
		</template>

		<template #headerExtra>
			<Badge type="splitted" bright size="small" :color="healthBadgeColor">
				<template #label>
					<span class="inline-flex items-center gap-1">
						<IndexIcon :health="index.health" color :size="14" />
						Health
					</span>
				</template>
				<template #value>{{ index.health }}</template>
			</Badge>
		</template>

		<template #footerMain>
			<div class="flex flex-wrap items-center gap-2">
				<Badge type="splitted" bright size="small">
					<template #label>Store</template>
					<template #value>{{ index.store_size }}</template>
				</Badge>
				<Badge type="splitted" bright size="small">
					<template #label>Docs</template>
					<template #value>{{ index.docs_count }}</template>
				</Badge>
				<Badge type="splitted" bright size="small">
					<template #label>Replicas</template>
					<template #value>{{ index.replica_count }}</template>
				</Badge>
			</div>
		</template>

		<template v-if="showActions" #footerExtra>
			<n-button quaternary type="error" size="small" @click.stop="handleDelete">
				<template #icon>
					<Icon :name="DeleteIcon" :size="15" />
				</template>
				Delete
			</n-button>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { BadgeColor } from "@/components/common/Badge.vue"
import type { ApiError } from "@/types/common"
import type { IndexStats } from "@/types/indices.d"
import { NButton, useDialog, useMessage } from "naive-ui"
import { computed, h, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import IndexIcon from "@/components/indices/IndexIcon.vue"
import { IndexHealth } from "@/types/indices.d"
import { getApiErrorMessage } from "@/utils"

const { index, showActions } = defineProps<{
	index: IndexStats
	showActions?: boolean
}>()

const emit = defineEmits<{
	(e: "delete"): void
}>()

const DeleteIcon = "carbon:trash-can"

const dialog = useDialog()
const message = useMessage()
const loading = ref(false)

const healthStatus = computed(() => {
	switch (index.health) {
		case IndexHealth.GREEN:
			return "success"
		case IndexHealth.YELLOW:
			return "warning"
		case IndexHealth.RED:
			return "error"
		default:
			return undefined
	}
})

const healthBadgeColor = computed((): BadgeColor | undefined => {
	switch (index.health) {
		case IndexHealth.GREEN:
			return "success"
		case IndexHealth.YELLOW:
			return "warning"
		case IndexHealth.RED:
			return "danger"
		default:
			return undefined
	}
})

function handleDelete() {
	dialog.warning({
		title: "Confirm",
		content: () =>
			h("div", {
				innerHTML: `Are you sure you want to delete the index:<br/><strong>${index.index}</strong> ?`
			}),
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deleteIndex()
		},
		onNegativeClick: () => {
			message.info("Delete canceled")
		}
	})
}

function deleteIndex() {
	loading.value = true

	Api.graylog
		.deleteIndex(index.index)
		.then(res => {
			if (res.data.success) {
				message.success("Index was successfully deleted.")

				emit("delete")
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (err.response?.status === 401) {
				message.error(
					getApiErrorMessage(err as ApiError) ||
						"Wazuh-Indexer returned Unauthorized. Please check your connector credentials."
				)
			} else if (err.response?.status === 404) {
				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
			} else {
				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loading.value = false
		})
}
</script>
