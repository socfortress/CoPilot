<template>
	<div class="flex flex-col gap-3">
		<p class="text-secondary text-sm">
			Static inspection runs on the CoPilot host in a locked-down container — the file is parsed, never executed.
		</p>

		<n-spin :show="uploading">
			<n-upload
				:show-file-list="false"
				:disabled="!customerCode || uploading"
				:custom-request="handleUpload"
				directory-dnd
			>
				<n-upload-dragger>
					<div class="flex flex-col items-center gap-2 py-6">
						<Icon :name="UploadIcon" :size="34" class="text-secondary" />
						<span class="text-sm font-medium">Click or drag a file here to analyze</span>
						<span class="text-secondary text-xs">
							{{
								customerCode
									? "Uploaded bytes never leave the host by default."
									: "Select a customer first."
							}}
						</span>
					</div>
				</n-upload-dragger>
			</n-upload>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { UploadCustomRequestOptions } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { ReputationMode } from "@/types/file-analysis"
import { NSpin, NUpload, NUploadDragger, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{ customerCode: string | null; sandbox: boolean; vtMode: ReputationMode }>()

// The panel starts the job; the shell owns where the analyst goes next, so both
// submission paths land on the result view the same way.
const emit = defineEmits<{ (e: "started", jobIds: string[]): void }>()

const message = useMessage()

const UploadIcon = "carbon:cloud-upload"

const uploading = ref(false)

function handleUpload({ file, onFinish, onError }: UploadCustomRequestOptions) {
	if (!file.file || !props.customerCode) {
		onError()
		return
	}
	uploading.value = true
	Api.fileAnalysis
		.upload(file.file, props.customerCode, { sandbox: props.sandbox, reputationMode: props.vtMode })
		.then(res => {
			if (res.data.success && res.data.job_id) {
				onFinish()
				emit("started", [res.data.job_id])
			} else {
				message.warning(res.data?.message || "Upload failed.")
				onError()
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Upload failed.")
			onError()
		})
		.finally(() => {
			uploading.value = false
		})
}
</script>
