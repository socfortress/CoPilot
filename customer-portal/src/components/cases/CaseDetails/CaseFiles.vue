<template>
	<div>
		<div class="mb-2 flex items-center justify-between">
			<label class="block text-sm font-medium text-gray-700">
				Case Files
				<span v-if="caseFiles.length > 0" class="font-normal text-gray-500">({{ caseFiles.length }})</span>
			</label>
			<div class="flex items-center space-x-2">
				<button
					class="inline-flex items-center rounded border border-transparent bg-indigo-100 px-2 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-200 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none"
					@click="openUploadForm"
				>
					<svg class="mr-1 h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
						></path>
					</svg>
					Upload File
				</button>
				<button
					v-if="!loadingFiles"
					class="text-xs text-indigo-600 hover:text-indigo-500 focus:outline-none"
					@click="loadCaseFiles(caseId)"
				>
					<svg class="mr-1 inline h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
						></path>
					</svg>
					Refresh
				</button>
			</div>
		</div>

		<!-- Upload Form -->
		<div v-if="showUploadForm" class="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-4">
			<div class="mb-3 flex items-center justify-between">
				<h4 class="text-sm font-medium text-blue-900">Upload File to Case</h4>
				<button class="text-blue-400 hover:text-blue-600" @click="closeUploadForm">
					<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						></path>
					</svg>
				</button>
			</div>

			<div class="space-y-3">
				<div>
					<input
						ref="fileInput"
						type="file"
						class="block w-full text-sm text-gray-500 file:mr-4 file:rounded-full file:border-0 file:bg-indigo-50 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-indigo-700 hover:file:bg-indigo-100 focus:outline-none"
						@change="handleFileSelect"
					/>
				</div>

				<div v-if="selectedFile" class="text-sm text-gray-600">
					Selected: {{ selectedFile.name }} ({{ formatBytes(selectedFile.size ?? 0) }})
				</div>

				<div class="flex justify-end space-x-2">
					<button
						type="button"
						class="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none"
						@click="closeUploadForm"
					>
						Cancel
					</button>
					<button
						:disabled="!selectedFile || uploadingFile"
						class="inline-flex items-center rounded-md border border-transparent bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
						@click="uploadFile"
					>
						<svg
							v-if="uploadingFile"
							class="mr-2 -ml-1 h-4 w-4 animate-spin text-white"
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
						>
							<circle
								class="opacity-25"
								cx="12"
								cy="12"
								r="10"
								stroke="currentColor"
								stroke-width="4"
							></circle>
							<path
								class="opacity-75"
								fill="currentColor"
								d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
							></path>
						</svg>
						{{ uploadingFile ? "Uploading..." : "Upload File" }}
					</button>
				</div>
			</div>
		</div>

		<!-- Loading Files -->
		<div v-if="loadingFiles" class="rounded-lg bg-gray-50 p-4 text-center">
			<div class="mx-auto h-6 w-6 animate-spin rounded-full border-b-2 border-indigo-600"></div>
			<p class="mt-2 text-sm text-gray-500">Loading files...</p>
		</div>

		<!-- Files List -->
		<div v-else-if="caseFiles.length > 0" class="max-h-64 overflow-y-auto rounded-lg bg-gray-50 p-4">
			<div
				v-for="file in caseFiles"
				:key="file.id"
				class="mb-3 border-b border-gray-200 pb-3 last:mb-0 last:border-b-0"
			>
				<div class="flex items-start justify-between">
					<div class="min-w-0 flex-1">
						<div class="flex items-center space-x-2">
							<svg
								class="h-4 w-4 shrink-0 text-gray-500"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
								></path>
							</svg>
							<p class="truncate text-sm font-medium text-gray-900">
								{{ file.file_name }}
							</p>
						</div>
						<div class="mt-1 flex items-center space-x-4 text-xs text-gray-500">
							<span>{{ formatBytes(file.file_size ?? 0) }}</span>
							<span v-if="file.content_type">{{ file.content_type }}</span>
							<span>{{ formatDate(file.upload_time, dFormats.datetime) }}</span>
						</div>
					</div>
					<button
						:disabled="downloadingFile === file.file_name"
						class="ml-3 inline-flex items-center rounded border border-transparent bg-indigo-100 px-2 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-200 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
						@click="downloadFile(caseId, file.file_name)"
					>
						<svg
							v-if="downloadingFile === file.file_name"
							class="mr-1 -ml-1 h-3 w-3 animate-spin text-indigo-700"
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
						>
							<circle
								class="opacity-25"
								cx="12"
								cy="12"
								r="10"
								stroke="currentColor"
								stroke-width="4"
							></circle>
							<path
								class="opacity-75"
								fill="currentColor"
								d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
							></path>
						</svg>
						<svg v-else class="mr-1 h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
							></path>
						</svg>
						{{ downloadingFile === file.file_name ? "Downloading..." : "Download" }}
					</button>
				</div>
			</div>
		</div>

		<!-- No Files Message -->
		<div v-else class="rounded-lg bg-gray-50 p-4 text-center">
			<svg class="mx-auto h-8 w-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
				></path>
			</svg>
			<p class="mt-2 text-sm text-gray-500">No files available for this case</p>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { CaseDataStoreFile } from "@/types/cases"
import type { ApiError } from "@/types/common"
import { saveAs } from "file-saver"
import { useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatBytes, formatDate } from "@/utils/format"

const { caseId } = defineProps<{
	caseId: number
}>()

const message = useMessage()
const dFormats = useSettingsStore().dateFormat

// Case files data
const caseFiles = ref<CaseDataStoreFile[]>([])
const loadingFiles = ref(false)
const downloadingFile = ref<string | null>(null)

// File upload data
const uploadingFile = ref(false)
const selectedFile = ref<File | null>(null)
const showUploadForm = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

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

function openUploadForm() {
	showUploadForm.value = true
	selectedFile.value = null
}

function closeUploadForm() {
	showUploadForm.value = false
	selectedFile.value = null
	if (fileInput.value) {
		fileInput.value.value = ""
	}
}

function handleFileSelect(event: Event) {
	const target = event.target as HTMLInputElement
	if (target.files && target.files.length > 0) {
		const file = target.files[0]
		// Check file size (e.g., limit to 50MB)
		const maxSize = 50 * 1024 * 1024 // 50MB in bytes
		if (file.size > maxSize) {
			message.error("File size too large. Maximum size is 50MB.")
			selectedFile.value = null
			return
		}
		selectedFile.value = file
	}
}

async function uploadFile() {
	if (!selectedFile.value || !caseId) return

	uploadingFile.value = true

	try {
		await Api.cases.uploadCaseFile(caseId, selectedFile.value)

		// Refresh the files list
		await loadCaseFiles(caseId)

		// Close the upload form
		closeUploadForm()
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
