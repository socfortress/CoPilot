<template>
	<n-spin :show="loading" class="flex min-h-48 grow flex-col" content-class="flex flex-col grow gap-4">
		<div>
			<n-collapse-transition :show="!showUploadForm">
				<n-button v-if="dataStore.length" :loading="uploading" type="primary" @click="openUploadForm()">
					<template #icon>
						<Icon :name="UploadIcon" />
					</template>
					Upload Data Store file
				</n-button>
			</n-collapse-transition>

			<n-collapse-transition :show="showUploadForm">
				<div class="flex flex-col gap-2">
					<n-upload v-model:file-list="fileList" :max="1" :disabled="uploading">
						<n-upload-dragger>
							<div>
								<Icon :name="UploadIcon" :size="28" :depth="3"></Icon>
							</div>
							<div class="font-semibold">Click or drag a file to this area to upload</div>
						</n-upload-dragger>
					</n-upload>

					<div class="flex items-center justify-end gap-3">
						<n-button quaternary :disabled="uploading" @click="closeUploadForm()">Close</n-button>

						<n-button
							:disabled="!isValid"
							:loading="uploading"
							type="primary"
							@click="uploadDataStoreFile()"
						>
							<template #icon>
								<Icon :name="UploadIcon" />
							</template>

							Upload
						</n-button>
					</div>
				</div>
			</n-collapse-transition>
		</div>

		<div class="flex flex-col gap-2">
			<template v-if="dataStore.length">
				<CaseDataStoreItem
					v-for="dataStoreFile of dataStore"
					:key="dataStoreFile.id"
					:data-store-file="dataStoreFile"
					embedded
					@deleted="deleteDataStoreFile(dataStoreFile)"
				/>
			</template>
			<template v-else>
				<n-collapse-transition :show="!showUploadForm">
					<n-empty v-if="!loading" class="min-h-48">
						<div class="flex flex-col items-center gap-4">
							<p>No files found</p>
							<n-button type="primary" :loading="uploading" @click="openUploadForm()">
								<template #icon>
									<Icon :name="UploadIcon" />
								</template>
								Upload a Data Store file
							</n-button>
						</div>
					</n-empty>
				</n-collapse-transition>
			</template>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { CaseDataStore } from "@/types/incidentManagement/cases.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import {
	NButton,
	NCollapseTransition,
	NEmpty,
	NSpin,
	NUpload,
	NUploadDragger,
	type UploadFileInfo,
	useMessage
} from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import CaseDataStoreItem from "./CaseDataStoreItem.vue"

const { caseId } = defineProps<{
	caseId: number
}>()

const emit = defineEmits<{
	(e: "deleted"): void
	(e: "updated"): void
}>()

const UploadIcon = "carbon:cloud-upload"
const message = useMessage()
const loading = ref(false)
const uploading = ref(false)
const showUploadForm = ref(false)
const dataStore = ref<CaseDataStore[]>([])
const fileList = ref<UploadFileInfo[]>([])
const newFile = computed<File | null>(() => fileList.value?.[0]?.file || null)

const isValid = computed(() => !!newFile.value)

function deleteDataStoreFile(dataStoreFile: CaseDataStore) {
	dataStore.value = dataStore.value.filter(o => o.id !== dataStoreFile.id)
	emit("deleted")
}

function updateDataStore(dataStoreFile: CaseDataStore) {
	fileList.value = []
	dataStore.value.push(dataStoreFile)
	emit("updated")
}

function openUploadForm() {
	showUploadForm.value = true
}

function closeUploadForm() {
	showUploadForm.value = false
}

function getCaseDataStore(caseId: number) {
	loading.value = true

	Api.incidentManagement
		.getCaseDataStoreFiles(caseId)
		.then(res => {
			if (res.data.success) {
				dataStore.value = res.data?.case_data_store || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

function uploadDataStoreFile() {
	if (!newFile.value) return

	uploading.value = true

	Api.incidentManagement
		.uploadCaseDataStoreFile(caseId, newFile.value)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Case Data Store File uploaded successfully")
				updateDataStore(res.data.case_data_store)
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			uploading.value = false
		})
}

onBeforeMount(() => {
	getCaseDataStore(caseId)
})
</script>
