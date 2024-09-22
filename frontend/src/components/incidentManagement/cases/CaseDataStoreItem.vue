<template>
	<div class="data-store-file" :class="{ embedded }">
		<n-spin :show="canceling">
			<div class="flex flex-col">
				<div class="header-box px-5 py-3 pb-0 flex justify-between items-center gap-3">
					<div class="id flex items-center">
						<span>
							#{{ dataStoreFile.id }}
							<span class="hidden xs:inline">- {{ dataStoreFile.bucket_name }}</span>
						</span>
					</div>
					<div class="time">
						<span v-if="dataStoreFile.upload_time">
							{{ formatDate(dataStoreFile.upload_time, dFormats.datetime) }}
						</span>
					</div>
				</div>

				<div class="main-box flex flex-col gap-3 px-5 py-3">
					<div class="content flex flex-col gap-1">
						<span>
							{{ dataStoreFile.file_name }}
						</span>

						<small v-if="dataStoreFile.file_hash" class="text-secondary-color font-mono hidden sm:inline">
							hash:
							{{ dataStoreFile.file_hash }}
						</small>
					</div>
				</div>

				<div class="footer-box px-5 py-3 flex justify-between items-center">
					<div class="details gap-3 items-center hidden sm:flex">
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
					<div class="actions-box flex flex-wrap gap-3 justify-end w-full sm:w-auto">
						<n-popconfirm
							v-model:show="showDeleteConfirm"
							trigger="manual"
							to="body"
							@positive-click="deleteDataStoreFile()"
							@clickoutside="showDeleteConfirm = false"
						>
							<template #trigger>
								<n-button
									quaternary
									size="tiny"
									:loading="canceling"
									@click.stop="showDeleteConfirm = true"
								>
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
				</div>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { CaseDataStore } from "@/types/incidentManagement/cases"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import bytes from "bytes"
import { saveAs } from "file-saver"
import { NButton, NPopconfirm, NSpin, useMessage } from "naive-ui"
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

<style lang="scss" scoped>
.data-store-file {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-050);
	overflow: hidden;

	.header-box {
		font-family: var(--font-family-mono);
		font-size: 13px;
		color: var(--fg-secondary-color);

		.id {
			word-break: break-word;
			line-height: 1.2;
		}

		.time {
			text-align: right;
		}
	}
	.main-box {
		.content {
			word-break: break-word;
		}
	}

	.footer-box {
		border-top: var(--border-small-100);
		font-size: 13px;
		background-color: var(--bg-secondary-color);
	}

	&.embedded {
		background-color: var(--bg-secondary-color);
		border: var(--border-small-100);

		.footer-box {
			background-color: var(--bg-body);
		}
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px var(--primary-color);
	}
}
</style>
