<template>
	<n-spin :show="loading" class="flex min-h-48 grow flex-col" content-class="flex flex-col grow gap-4">
		<div>
			<n-collapse-transition :show="!showUploadForm">
				<div class="flex flex-wrap items-center gap-3">
					<n-button v-if="templateNameList.length" type="primary" @click="openUploadForm()">
						<template #icon>
							<Icon :name="UploadIcon" />
						</template>
						Upload Report Template file
					</n-button>

					<n-button
						v-if="!isDefaultTemplatePresent && templateNameList.length"
						:loading="checkingDefaultTemplate"
						@click="uploadDefaultTemplate()"
					>
						<template #icon>
							<Icon :name="DefaultTemplateIcon" />
						</template>
						Load the SOCFortress Template
					</n-button>
				</div>
			</n-collapse-transition>

			<n-collapse-transition :show="showUploadForm">
				<div class="flex flex-col gap-2">
					<n-upload
						v-model:file-list="fileList"
						:max="1"
						:disabled="uploading"
						accept="application/vnd.openxmlformats-officedocument.wordprocessingml.document, .docx, .DOCX"
					>
						<n-upload-dragger>
							<div>
								<Icon :name="UploadIcon" :size="28" :depth="3"></Icon>
							</div>
							<div class="font-semibold">Click or drag a file to this area to upload</div>
							<p class="mt-2">Only .docx files are accepted</p>
						</n-upload-dragger>
					</n-upload>

					<div class="flex items-center justify-end gap-3">
						<n-button quaternary :disabled="uploading" @click="closeUploadForm()">Close</n-button>

						<n-button
							:disabled="!isValid"
							:loading="uploading"
							type="primary"
							@click="uploadCustomTemplate()"
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
			<template v-if="templateNameList.length">
				<n-card
					v-for="templateName of templateNameList"
					:key="templateName"
					size="small"
					class="overflow-hidden"
					content-class="flex justify-between items-center bg-secondary flex-wrap gap-4"
				>
					<div class="flex gap-3">
						<n-tooltip to="body">
							<template #trigger>
								<n-button
									size="tiny"
									type="primary"
									text
									:loading="downloading === templateName"
									@click="downloadTemplate(templateName)"
								>
									<template #icon>
										<Icon :name="DownloadIcon" />
									</template>
								</n-button>
							</template>
							Download
						</n-tooltip>
						<span>
							{{ templateName }}
						</span>
					</div>

					<n-popconfirm to="body" @positive-click="deleteTemplate(templateName)">
						<template #trigger>
							<n-button quaternary size="tiny">Delete</n-button>
						</template>
						Are you sure you want to delete this template?
					</n-popconfirm>
				</n-card>
			</template>
			<template v-else>
				<n-collapse-transition :show="!showUploadForm">
					<n-empty v-if="!loading" class="min-h-48">
						<div class="flex flex-col items-center gap-4">
							<p>No templates found</p>
							<div class="flex flex-wrap items-center gap-3">
								<n-button type="primary" :loading="uploading" @click="openUploadForm()">
									<template #icon>
										<Icon :name="UploadIcon" />
									</template>
									Upload a Report Template file
								</n-button>
								<n-button :loading="uploading" @click="uploadDefaultTemplate()">
									<template #icon>
										<Icon :name="DefaultTemplateIcon" />
									</template>
									Load the SOCFortress Template
								</n-button>
							</div>
						</div>
					</n-empty>
				</n-collapse-transition>
			</template>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useCaseReportTemplateStore } from "@/stores/caseReportTemplate"
import saveAs from "file-saver"
import {
	NButton,
	NCard,
	NCollapseTransition,
	NEmpty,
	NPopconfirm,
	NSpin,
	NTooltip,
	NUpload,
	NUploadDragger,
	type UploadFileInfo,
	useMessage
} from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"

const UploadIcon = "carbon:cloud-upload"
const DownloadIcon = "carbon:document-download"
const DefaultTemplateIcon = "carbon:document-sketch"
const caseReportTemplateStore = useCaseReportTemplateStore()
const message = useMessage()
const loadingList = computed(() => caseReportTemplateStore.loading)
const uploading = ref(false)
const canceling = ref(false)
const checkingDefaultTemplate = ref(false)
const downloading = ref<false | string>(false)
const loading = computed(() => loadingList.value || uploading.value || canceling.value)
const showUploadForm = ref(false)
const templateNameList = computed(() => caseReportTemplateStore.templatesList)
const fileList = ref<UploadFileInfo[]>([])
const newFile = computed<File | null>(() => fileList.value?.[0]?.file || null)
const isValid = computed(() => !!newFile.value)
const isDefaultTemplatePresent = ref(true)

function openUploadForm() {
	showUploadForm.value = true
}

function closeUploadForm() {
	showUploadForm.value = false
}

function uploadCustomTemplate() {
	if (!newFile.value) return

	uploading.value = true

	caseReportTemplateStore
		.uploadCustomTemplate(newFile.value)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Case Report Template uploaded successfully")
				fileList.value = []
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

function uploadDefaultTemplate() {
	uploading.value = true

	Api.incidentManagement
		.uploadDefaultCaseReportTemplate()
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Case Report Template uploaded successfully")
				refreshTemplates()
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

function checkDefaultCaseReportTemplateExists() {
	checkingDefaultTemplate.value = true

	Api.incidentManagement
		.checkDefaultCaseReportTemplateExists()
		.then(res => {
			if (res.data.success) {
				isDefaultTemplatePresent.value = res.data.default_template_exists
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			checkingDefaultTemplate.value = false
		})
}

function downloadTemplate(templateName: string) {
	downloading.value = templateName

	Api.incidentManagement
		.downloadCaseReportTemplate(templateName)
		.then(res => {
			if (res.data) {
				saveAs(res.data, templateName)
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

function deleteTemplate(templateName: string) {
	canceling.value = true

	caseReportTemplateStore
		.deleteTemplate(templateName)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Case Report Template deleted successfully")
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

function refreshTemplates() {
	caseReportTemplateStore.refreshTemplates().catch(err => {
		message.error(err.response?.data?.message || "An error occurred. Please try again later.")
	})
}

watch(templateNameList, () => {
	checkDefaultCaseReportTemplateExists()
})

onBeforeMount(() => {
	refreshTemplates()
})
</script>
