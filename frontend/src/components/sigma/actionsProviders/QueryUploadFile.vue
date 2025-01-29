<template>
	<n-popover v-model:show="show" trigger="manual" to="body" content-class="px-0" @clickoutside="closePopup()">
		<template #trigger>
			<slot :loading :toggle-popup />
		</template>

		<div class="flex max-w-80 flex-col gap-2 py-1">
			<n-upload
				v-model:file-list="fileList"
				:max="1"
				accept="application/x-yaml, .yaml, .YAML, .yml, .YML"
				:disabled="loading"
			>
				<n-upload-dragger>
					<div>
						<Icon :name="UploadIcon" :size="28" :depth="3"></Icon>
					</div>
					<div class="font-semibold">Click or drag a file to this area to upload</div>
					<p class="mt-2">Only .yaml files are accepted</p>
				</n-upload-dragger>
			</n-upload>

			<div class="flex justify-between gap-2">
				<n-button quaternary size="small" @click="closePopup()">Close</n-button>
				<n-button :disabled="!isValid" :loading type="primary" size="small" @click="uploadQueries()">
					Upload
				</n-button>
			</div>
		</div>
	</n-popover>
</template>

<script setup lang="ts">
import type { UploadFileInfo } from "naive-ui"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { NButton, NPopover, NUpload, NUploadDragger, useMessage } from "naive-ui"
import { computed, ref } from "vue"

const emit = defineEmits<{
	(e: "updated"): void
}>()

const loading = defineModel<boolean | undefined>("loading", { default: false })

const UploadIcon = "carbon:document-add"

const show = ref(false)
const lastShow = ref(new Date().getTime())
const message = useMessage()
const fileList = ref<UploadFileInfo[]>([])
const yamlFile = computed<File | null>(() => fileList.value?.[0]?.file || null)
const isValid = computed(() => fileList.value.length)

function togglePopup() {
	if (new Date().getTime() - lastShow.value > 500) {
		show.value = !show.value
	}
}

function closePopup() {
	lastShow.value = new Date().getTime()
	show.value = false
}

function uploadQueries() {
	loading.value = true

	if (yamlFile.value) {
		Api.sigma
			.uploadRulesFile(yamlFile.value)
			.then(res => {
				if (res.data.success) {
					emit("updated")
					fileList.value = []
					message.success(res.data?.message || "Successfully uploaded the Sigma queries to the database")
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
}
</script>
