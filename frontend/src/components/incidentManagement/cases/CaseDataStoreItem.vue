<template>
	<CardEntity :loading="canceling" :embedded hoverable>
		<template #headerMain>
			<div class="flex items-center">
				<span>
					#{{ dataStoreFile.id }}
					<span class="xs:inline hidden">- {{ dataStoreFile.bucket_name }}</span>
				</span>
			</div>
		</template>
		<template v-if="dataStoreFile.upload_time" #headerExtra>
			{{ formatDate(dataStoreFile.upload_time, dFormats.datetime) }}
		</template>
		<template #default>
			<div class="flex flex-col gap-1">
				{{ dataStoreFile.file_name }}

				<p v-if="dataStoreFile.file_hash" class="hidden font-mono text-sm sm:inline">
					hash:
					{{ dataStoreFile.file_hash }}
				</p>
			</div>
		</template>
		<template #footerMain>
			<div class="hidden flex-wrap items-center gap-3 sm:flex">
				<Badge v-if="dataStoreFile.content_type" type="splitted">
					<template #label>type</template>
					<template #value>
						{{ dataStoreFile.content_type }}
					</template>
				</Badge>
				<Badge v-if="dataStoreFile.file_size" type="splitted">
					<template #label>size</template>
					<template #value>
						{{ prettyBytes }}
					</template>
				</Badge>
			</div>
		</template>
		<template #footerExtra>
			<div class="flex flex-wrap gap-3">
				<n-popconfirm
					v-model:show="showDeleteConfirm"
					trigger="manual"
					to="body"
					@positive-click="deleteDataStoreFile()"
					@clickoutside="showDeleteConfirm = false"
				>
					<template #trigger>
						<n-button quaternary size="tiny" :loading="canceling" @click.stop="showDeleteConfirm = true">
							Delete
						</n-button>
					</template>
					Are you sure you want to delete this file?
				</n-popconfirm>

				<n-button size="tiny" type="primary" :loading="downloading" @click.stop="downloadFile()">
					<template #icon>
						<Icon :name="DownloadIcon" />
					</template>

					Download
				</n-button>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { CaseDataStore } from "@/types/incidentManagement/cases"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import bytes from "bytes"
import { saveAs } from "file-saver"
import { NButton, NPopconfirm, useMessage } from "naive-ui"
import { computed, ref } from "vue"

const { dataStoreFile, embedded } = defineProps<{
	dataStoreFile: CaseDataStore
	embedded?: boolean
}>()

const emit = defineEmits<{
	(e: "opened"): void
	(e: "deleted"): void
}>()

const DownloadIcon = "carbon:cloud-download"
const message = useMessage()
const canceling = ref(false)
const downloading = ref(false)
const showDeleteConfirm = ref(false)
const dFormats = useSettingsStore().dateFormat
const prettyBytes = computed(() => bytes(dataStoreFile.file_size))

function downloadFile() {
	downloading.value = true

	Api.incidentManagement
		.downloadCaseDataStoreFile(dataStoreFile.case_id, dataStoreFile.file_name)
		.then(res => {
			if (res.data) {
				saveAs(res.data, dataStoreFile.file_name)
			} else {
				message.warning("An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			downloading.value = false
		})
}

function deleteDataStoreFile() {
	canceling.value = true

	Api.incidentManagement
		.deleteCaseDataStoreFile(dataStoreFile.case_id, dataStoreFile.file_name)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Case Data Store File deleted successfully")
				emit("deleted")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			canceling.value = false
		})
}
</script>
