<template>
	<n-spin :show="uploading">
		<div class="flex flex-col gap-3">
			<div class="flex flex-col gap-1">
				<n-upload v-model:file-list="fileList" :max="1" :disabled="uploading">
					<n-upload-dragger>
						<div>
							<Icon :name="UploadIcon" :size="28" :depth="3" />
						</div>
						<div class="font-medium">Click or drag a file to this area to upload</div>
					</n-upload-dragger>
				</n-upload>
				<n-collapse-transition :show="!!newFile">
					<div class="mt-1 flex justify-end">
						<n-checkbox v-model:checked="isPasswordProtected">It is password protected</n-checkbox>
					</div>
				</n-collapse-transition>
				<n-collapse-transition :show="!!newFile && isPasswordProtected">
					<n-input
						v-model:value="filePassword"
						type="password"
						show-password-on="click"
						class="mt-3"
						placeholder="File password"
					/>
				</n-collapse-transition>
			</div>
			<div class="mb-2 flex justify-end">
				<n-button type="primary" :disabled="!isValid" :loading="uploading" @click="submit()">Submit</n-button>
			</div>
			<div v-if="error" class="response bg-secondary error">
				<div class="px-4 py-2.5">
					{{ error }}
				</div>
			</div>
			<div v-else class="flex flex-col gap-3">
				<div v-if="fileResponse" class="response bg-secondary p-4">
					<div class="flex flex-col gap-4 text-sm">
						<div class="font-semibold">
							This link gives you access to the instance created from your uploaded file.
						</div>
						<n-alert type="warning">
							<template #icon>
								<Icon name="carbon:warning-alt" :size="14" />
							</template>
							<template #header>
								<div class="text-xs">Please note</div>
							</template>
							<template #default>
								<div class="text-xs">
									Once you close this window, the link cannot be retrieved again. If you think you
									might need it later, make sure to copy and save it.
								</div>
							</template>
						</n-alert>
						<div>
							<a
								:href="fileResponse.links.self"
								target="_blank"
								alt="references url"
								rel="nofollow noopener noreferrer"
								class="leading-6"
							>
								<span>
									{{ fileResponse.links.self }}
								</span>
								<Icon :name="LinkIcon" :size="14" class="relative top-0.5 ml-2" />
							</a>
						</div>
						<div v-if="isCopySupported" class="flex justify-end">
							<n-tooltip :show="showCopyTooltip" trigger="manual">
								<template #trigger>
									<n-button size="small" secondary @click="copyLink()">
										<template #icon>
											<Icon name="carbon:copy" :size="14" />
										</template>
										Copy
									</n-button>
								</template>
								<div class="text-xs">Copied!</div>
							</n-tooltip>
						</div>
					</div>
				</div>
				<div
					v-if="fileResponse && !analysisResponse"
					class="response bg-secondary flex flex-wrap items-center gap-2 p-4"
				>
					<Icon :name="LoadingIcon" :size="16" class="relative top-0.5" />
					analyzing...
				</div>
				<n-spin v-if="analysisResponse" :show="loading">
					<div class="response bg-secondary overflow-hidden">
						<div class="bg-default flex items-center justify-between p-4">
							<div>Analysis</div>
							<n-button :loading secondary size="small" @click="analysis()">
								<template #icon>
									<Icon :name="RefreshIcon" :size="14" />
								</template>
								Reload
							</n-button>
						</div>
						<div class="divide-border flex flex-col divide-y-2 text-sm">
							<div class="flex flex-col gap-1 p-4">
								<div class="text-secondary text-xs">status</div>
								<div
									class="flex items-center gap-1"
									:class="{
										'text-success': analysisResponse.attributes.status === 'completed',
										'text-warning': analysisResponse.attributes.status === 'queued'
									}"
								>
									<Icon
										:name="
											analysisResponse.attributes.status === 'completed'
												? 'carbon:checkmark-outline'
												: 'carbon:hourglass'
										"
										:size="14"
									/>
									{{ analysisResponse.attributes.status }}
								</div>
							</div>
							<div v-if="!_isEmpty(analysisResponse.attributes.stats)" class="flex flex-col gap-1 p-4">
								<div class="text-secondary text-xs">stats</div>
								<div class="divide-border flex flex-col gap-2 divide-y">
									<div
										v-for="(val, key) of analysisResponse.attributes.stats"
										:key="key"
										class="flex items-end justify-between gap-4"
									>
										<div>{{ key }}</div>
										<div class="text-right font-mono">{{ val }}</div>
									</div>
								</div>
							</div>
							<div
								v-if="!_isEmpty(analysisResponse.attributes.results)"
								class="flex flex-col gap-2 overflow-hidden p-4"
							>
								<div class="text-secondary flex items-center justify-between text-xs">
									<div>results</div>
									<n-button
										size="tiny"
										secondary
										@click="analysisResultCollapsed = !analysisResultCollapsed"
									>
										<template #icon>
											<Icon
												:name="
													analysisResultCollapsed
														? 'carbon:chevron-right'
														: 'carbon:chevron-down'
												"
												:size="14"
											/>
										</template>
										{{ analysisResultCollapsed ? "expand" : "collapse" }}
									</n-button>
								</div>
								<div v-if="!analysisResultCollapsed" class="flex flex-col gap-4">
									<div
										v-for="(resultVal, resultKey) of analysisResponse.attributes.results"
										:key="resultKey"
										class="border-default border"
									>
										<div class="px-2 py-1">{{ resultKey }}</div>
										<div class="divide-border bg-default flex flex-col gap-1 divide-y">
											<div
												v-for="(val, key) of resultVal"
												:key="key"
												class="flex items-end justify-between gap-4 px-2 py-0.5"
											>
												<div>{{ key }}</div>
												<div class="text-right font-mono">{{ val || "—" }}</div>
											</div>
										</div>
									</div>
								</div>
							</div>
							<div v-if="!_isEmpty(analysisResponse.links)" class="flex flex-col gap-1 p-4">
								<div class="text-secondary text-xs">links</div>
								<div class="divide-border flex flex-col gap-2 divide-y">
									<div
										v-for="(val, key) of analysisResponse.links"
										:key="key"
										class="flex items-end justify-between"
									>
										<a
											:href="val"
											target="_blank"
											alt="references url"
											rel="nofollow noopener noreferrer"
											class="leading-6"
										>
											<span>
												{{ val }}
											</span>
											<Icon :name="LinkIcon" :size="14" class="relative top-0.5 ml-2" />
										</a>
									</div>
								</div>
							</div>
						</div>
					</div>
				</n-spin>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { UploadFileInfo } from "naive-ui"
import type { VirusTotalAnalysis, VirusTotalFileCheckResponse } from "@/types/threatIntel.d"
import { useClipboard } from "@vueuse/core"
import _isEmpty from "lodash/isEmpty"
import {
	NAlert,
	NButton,
	NCheckbox,
	NCollapseTransition,
	NInput,
	NSpin,
	NTooltip,
	NUpload,
	NUploadDragger,
	useMessage
} from "naive-ui"
import { computed, onMounted, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

const emit = defineEmits<{
	(
		e: "mounted",
		value: {
			restore: () => void
		}
	): void
}>()

const LinkIcon = "carbon:launch"
const RefreshIcon = "carbon:renew"
const LoadingIcon = "eos-icons:loading"
const UploadIcon = "carbon:cloud-upload"

const message = useMessage()
const loading = ref(false)
const uploading = ref(false)
const analysisResultCollapsed = ref(true)
const fileResponse = ref<VirusTotalFileCheckResponse | null>(null)
const analysisResponse = ref<VirusTotalAnalysis | null>(null)
const error = ref<string>("")
const fileList = ref<UploadFileInfo[]>([])
const newFile = computed<File | null>(() => fileList.value?.[0]?.file || null)
const isPasswordProtected = ref(false)
const filePassword = ref<string | null>(null)
let abortController: AbortController | null = null

const fileLink = computed(() => fileResponse.value?.links.self || "")
const { copy: copyLink, copied: showCopyTooltip, isSupported: isCopySupported } = useClipboard({ source: fileLink })

const isValid = computed(() => {
	if (isPasswordProtected.value && !filePassword.value) {
		return false
	}

	return !!newFile.value
})

function restore() {
	fileList.value = []
	loading.value = false
	uploading.value = false
	fileResponse.value = null
	analysisResponse.value = null
	error.value = ""
	abortController?.abort()
}

function submit() {
	if (!newFile.value) return

	uploading.value = true

	Api.threatIntel
		.virusTotalFileCheck(newFile.value, filePassword.value || undefined)
		.then(res => {
			if (res.data.success) {
				error.value = ""
				fileResponse.value = res.data.data
				analysisResponse.value = null

				analysis()
				message.success(res.data?.message || "File submitted successfully for analysis.")
			} else {
				error.value = res.data?.message || "An error occurred. Please try again later."
				message.warning(error.value)
			}
		})
		.catch(err => {
			error.value = err.response?.data?.message || "An error occurred. Please try again later."
			message.error(error.value)
		})
		.finally(() => {
			uploading.value = false
		})
}

function analysis() {
	abortController?.abort()

	if (!fileResponse.value?.id) return

	loading.value = true
	abortController = new AbortController()

	Api.threatIntel
		.virusTotalAnalysis(fileResponse.value.id, abortController.signal)
		.then(res => {
			if (res.data.success) {
				error.value = ""
				analysisResponse.value = res.data.data
				message.success(res.data?.message || "Analysis status retrieved successfully.")
			} else {
				error.value = res.data?.message || "An error occurred. Please try again later."
				message.warning(error.value)
			}
		})
		.catch(err => {
			error.value = err.response?.data?.message || "An error occurred. Please try again later."
			message.error(error.value)
		})
		.finally(() => {
			loading.value = false
		})
}

watch(newFile, () => {
	isPasswordProtected.value = false
})

watch(isPasswordProtected, () => {
	filePassword.value = null
})

onMounted(() => {
	emit("mounted", {
		restore
	})
})
</script>

<style scoped lang="scss">
.response {
	border-radius: var(--border-radius);
	border: 1px solid var(--success-color);

	&.error {
		border-color: var(--error-color);
	}
}
</style>
