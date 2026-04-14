<template>
	<div class="flex flex-col gap-4">
		<div class="flex items-center justify-between gap-4">
			<Chip v-if="caseFiles.length" :value="loadingFiles ? 'Loading...' : caseFiles.length" label="files" />
		</div>

		<n-spin :show="loadingFiles">
			<!-- Files List -->
			<div v-if="caseFiles.length" class="flex flex-col gap-2">
				<CardEntity v-for="file in caseFiles" :key="file.id">
					<template #header-main>{{ file.file_name }}</template>
					<template #header-extra>{{ formatDate(file.upload_time, dFormats.datetime) }}</template>
					<template #default>
						<div class="flex flex-wrap gap-2">
							<Chip :value="formatBytes(file.file_size ?? 0)" label="size" />
							<Chip :value="file.content_type" label="type" />
						</div>
					</template>
					<template #footer-extra>
						<div class="flex flex-wrap items-center justify-end gap-2">
							<n-button
								type="primary"
								secondary
								size="small"
								:loading="downloadingFile === file.file_name"
								@click="downloadFile(caseId, file.file_name)"
							>
								<template #icon>
									<Icon name="carbon:download" />
								</template>
								Download
							</n-button>

							<n-popconfirm to="body" @positive-click="deleteFile(caseId, file.file_name)">
								<template #trigger>
									<n-button
										size="small"
										:focusable="false"
										:loading="deletingFile === file.file_name"
									>
										<template #icon>
											<Icon name="carbon:trash-can" />
										</template>
										Delete
									</n-button>
								</template>
								Are you sure you want to delete this file?
							</n-popconfirm>
						</div>
					</template>
				</CardEntity>
			</div>

			<n-empty v-else description="No files found" class="min-h-50 justify-center" />
		</n-spin>

		<div class="flex flex-col gap-2">
			<n-upload v-model:file-list="fileList" :max="1" :disabled="uploadingFile">
				<n-upload-dragger>
					<div>
						<Icon name="carbon:document-add" :size="28" :depth="3" />
					</div>
					<div class="font-semibold">Click or drag a file to this area to upload</div>
				</n-upload-dragger>
			</n-upload>
			<div class="flex justify-end">
				<n-button
					type="primary"
					secondary
					:disabled="!selectedFile"
					:loading="uploadingFile"
					@click="uploadFile"
				>
					<template #icon>
						<Icon name="carbon:cloud-upload" />
					</template>
					Upload
				</n-button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { UploadFileInfo } from "naive-ui"
import type { CaseDataStoreFile } from "@/types/cases"
import type { ApiError } from "@/types/common"
import { saveAs } from "file-saver"
import { NButton, NEmpty, NPopconfirm, NSpin, NUpload, NUploadDragger, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Chip from "@/components/common/Chip.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatBytes, formatDate } from "@/utils/format"

const { caseId } = defineProps<{
	caseId: number
}>()

const message = useMessage()
const dFormats = useSettingsStore().dateFormat

const caseFiles = ref<CaseDataStoreFile[]>([])
const loadingFiles = ref(false)
const downloadingFile = ref<string | null>(null)
const deletingFile = ref<string | null>(null)
const uploadingFile = ref(false)
const fileList = ref<UploadFileInfo[]>([])
const selectedFile = computed<File | null>(() => fileList.value?.[0]?.file || null)

async function loadCaseFiles(caseId: number) {
	loadingFiles.value = true

	try {
		const response = await Api.cases.getCaseFiles(caseId)
		caseFiles.value = response.data.case_data_store
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
		caseFiles.value = []
	} finally {
		loadingFiles.value = false
	}
}

async function downloadFile(caseId: number, fileName: string) {
	downloadingFile.value = fileName

	try {
		const blob = await Api.cases.downloadCaseFile(caseId, fileName)
		saveAs(blob.data, fileName)
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		downloadingFile.value = null
	}
}

async function deleteFile(caseId: number, fileName: string) {
	deletingFile.value = fileName

	try {
		await Api.cases.deleteCaseFile(caseId, fileName)
		loadCaseFiles(caseId)
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		deletingFile.value = null
	}
}

async function uploadFile() {
	if (!selectedFile.value || !caseId) return

	uploadingFile.value = true

	try {
		await Api.cases.uploadCaseFile(caseId, selectedFile.value)

		loadCaseFiles(caseId)
		fileList.value = []
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		uploadingFile.value = false
	}
}

// Lifecycle
onBeforeMount(() => {
	loadCaseFiles(caseId)
})
</script>
