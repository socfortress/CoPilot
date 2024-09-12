<template>
	<n-popover trigger="manual" to="body" content-class="px-0" v-model:show="show" @clickoutside="closePopup()">
		<template #trigger>
			<slot :loading :togglePopup />
		</template>

		<div class="py-1 flex flex-col gap-2 max-w-80">
			<n-upload
				:max="1"
				accept="application/x-yaml, .yaml, .YAML, .yml, .YML"
				v-model:file-list="fileList"
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

			<div class="flex gap-2 justify-between">
				<n-button @click="closePopup()" quaternary size="small">Close</n-button>
				<n-button :disabled="!isValid" :loading @click="uploadQueries()" type="primary" size="small">
					Upload
				</n-button>
			</div>
		</div>
	</n-popover>
</template>

<script setup lang="ts">
import { computed, ref } from "vue"
import { NButton, NPopover, NUpload, NUploadDragger, useMessage, type UploadFileInfo } from "naive-ui"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

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
