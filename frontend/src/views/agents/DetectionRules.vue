<template>
	<div class="page page-wrapped page-mobile-full page-without-footer flex flex-col">
		<SegmentedPage
			main-content-class="!p-0 overflow-hidden grow flex flex-col h-full"
			:use-main-scroll="false"
			padding="18px"
			enable-resize
			toolbar-height="54px"
			sidebar-content-class="p-0!"
		>
			<template #sidebar-header>
				<div class="flex w-full items-center justify-between gap-3">
					<n-input
						v-model:value="filters.search"
						size="small"
						class="max-w-full grow"
						clearable
						placeholder="Search..."
					>
						<template #prefix>
							<Icon :name="SearchIcon" :size="16" />
						</template>
					</n-input>

					<n-tooltip>
						<template #trigger>
							<n-button secondary :loading="loadingManager" size="small" @click="reloadManager()">
								<template #icon>
									<Icon :name="RefreshIcon"></Icon>
								</template>
							</n-button>
						</template>
						<div>Restart Wazuh</div>
					</n-tooltip>
				</div>
			</template>
			<template #sidebar-content>
				<n-spin :show="loadingList">
					<template v-if="fileList.length">
						<div class="divide-border flex flex-col divide-y-1">
							<div
								v-for="item of fileList"
								:key="item.filename"
								class="hover:text-warning cursor-pointer px-4.5 py-2.5 font-mono text-sm break-all"
								:class="{ 'bg-warning/10': item.filename === currentFile?.filename }"
								@click.stop="loadFile(item.filename)"
							>
								{{ item.filename }}
							</div>
						</div>
					</template>
					<template v-else>
						<n-empty v-if="!loadingList" description="No items found" class="h-48 justify-center" />
					</template>
				</n-spin>
			</template>
			<template v-if="pagination.total" #sidebar-footer>
				<div class="flex w-full items-center justify-center">
					<n-pagination
						v-model:page="pagination.current"
						:page-size="pagination.size"
						:page-slot="5"
						:item-count="pagination.total"
						simple
					/>
				</div>
			</template>
			<template v-if="currentFile" #main-toolbar>
				<div class="@container flex items-center justify-between">
					<div class="flex items-center gap-2 md:gap-3">
						<n-button
							v-if="xmlEditorCTX"
							size="small"
							:disabled="!xmlEditorCTX.canUndo()"
							@click="xmlEditorCTX.undo"
						>
							<div class="flex items-center gap-2">
								<Icon :name="UndoIcon" />
								<span class="hidden @sm:flex">Undo</span>
							</div>
						</n-button>
						<n-button
							v-if="xmlEditorCTX"
							size="small"
							:disabled="!xmlEditorCTX.canRedo()"
							@click="xmlEditorCTX.redo"
						>
							<div class="flex items-center gap-2">
								<span class="hidden @sm:flex">Redo</span>
								<Icon :name="RedoIcon" />
							</div>
						</n-button>
					</div>
					<div class="flex items-center gap-2 md:gap-3">
						<n-popover v-if="xmlErrors.length && xmlEditorCTX" class="p-1!">
							<template #trigger>
								<div class="flex items-center justify-end gap-2">
									<Icon
										name="carbon:warning-alt"
										:size="20"
										class="text-warning animate-fade cursor-help"
									/>
									<span class="text-warning hidden font-mono text-xs @lg:flex">Errors detected</span>
								</div>
							</template>

							<n-scrollbar class="max-h-100">
								<div class="flex max-w-80 flex-col gap-1">
									<div
										v-for="item of xmlErrors"
										:key="JSON.stringify(item)"
										class="bg-secondary hover:bg-body flex cursor-pointer flex-col gap-0.5 rounded-sm p-1 font-mono"
										@click="xmlEditorCTX.scrollToLine(item.line)"
									>
										<div class="text-secondary text-[8px]">line: {{ item.line }}</div>
										<div class="text-xs">{{ item.message }}</div>
									</div>
								</div>
							</n-scrollbar>
						</n-popover>

						<n-button
							:loading="uploadingFile"
							size="small"
							type="primary"
							:disabled="!isDirty"
							@click="uploadFileFile()"
						>
							<div class="flex items-center gap-2">
								<Icon :name="UploadIcon" />
								<span class="hidden @xs:flex">Upload</span>
							</div>
						</n-button>
					</div>
				</div>
			</template>
			<template #main-content>
				<div v-if="currentFile" class="px-4.5 py-2.5 font-mono text-sm break-all">
					current file: {{ currentFile?.filename }}
				</div>
				<n-spin
					:show="loadingFile || uploadingFile"
					class="flex h-full w-full overflow-hidden"
					content-class="flex h-full grow flex-col justify-center overflow-hidden"
				>
					<template v-if="currentFile">
						<XMLEditor
							v-model="currentFile.content"
							class="scrollbar-styled text-sm"
							@errors="xmlErrors = $event"
							@mounted="xmlEditorCTX = $event"
						/>
					</template>
					<template v-else>
						<n-empty v-if="!loadingFile" description="Select a customer" class="h-48 justify-center" />
					</template>
				</n-spin>
			</template>
		</SegmentedPage>
	</div>
</template>

<script setup lang="ts">
import type { XMLEditorCtx, XMLError } from "@/components/common/XMLEditor.vue"
import type { WazuhFileDetails, WazuhFileItem } from "@/types/wazuh/rules.d"
import { watchDebounced } from "@vueuse/core"
import axios from "axios"
import _clone from "lodash/cloneDeep"
import { NButton, NEmpty, NInput, NPagination, NPopover, NScrollbar, NSpin, NTooltip, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import SegmentedPage from "@/components/common/SegmentedPage.vue"
import XMLEditor from "@/components/common/XMLEditor.vue"

const message = useMessage()
const loadingManager = ref(false)
const loadingList = ref(false)
const loadingFile = ref(false)
const uploadingFile = ref(false)
const fileList = ref<WazuhFileItem[]>([])
const currentFile = ref<WazuhFileDetails | null>(null)
const backupFile = ref<WazuhFileDetails | null>(null)
const xmlEditorCTX = ref<XMLEditorCtx | null>(null)
const UndoIcon = "carbon:undo"
const RedoIcon = "carbon:redo"
const SearchIcon = "ion:search-outline"
const RefreshIcon = "carbon:renew"
const UploadIcon = "carbon:cloud-upload"

const filters = ref({
	search: null
})
const pagination = ref({
	current: 1,
	size: 30,
	total: 0
})

const isDirty = computed(() => currentFile.value?.content !== backupFile.value?.content)
const xmlErrors = ref<XMLError[]>([])

let abortController: AbortController | null = null

function loadFile(filename: string) {
	if (filename !== currentFile.value?.filename) {
		getFile(filename)
	}
}

function reloadManager() {
	abortController?.abort()

	loadingManager.value = true

	Api.wazuh.rules
		.restartManager()
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Wazuh Manager cluster restarted successfully")
				getList()
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingManager.value = false
		})
}

function getList() {
	abortController?.abort()
	abortController = new AbortController()

	loadingList.value = true

	Api.wazuh.rules
		.getRulesFileList(
			{
				search: filters.value.search || undefined,
				pretty: false,
				wait_for_complete: false,
				distinct: false,
				offset: (pagination.value.current - 1) * pagination.value.size,
				limit: pagination.value.size
			},
			abortController.signal
		)
		.then(res => {
			if (res.data.success) {
				fileList.value = res.data.results || []
				pagination.value.total = res.data.total_items
			} else {
				pagination.value.total = 0
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
			loadingList.value = false
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				fileList.value = []

				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
				loadingList.value = false
			}
		})
}

function getFile(filename: string) {
	loadingFile.value = true

	Api.wazuh.rules
		.getRulesFile(filename)
		.then(res => {
			if (res.data.success) {
				currentFile.value = _clone(res.data)
				backupFile.value = _clone(res.data)
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingFile.value = false
		})
}

function uploadFileFile() {
	if (currentFile.value) {
		uploadingFile.value = true

		Api.wazuh.rules
			.updateRulesFile(
				currentFile.value.filename,
				new File([currentFile.value.content], currentFile.value.filename, {
					type: "text/xml;charset=utf-8"
				})
			)

			.then(res => {
				if (res.data.success) {
					currentFile.value = _clone(currentFile.value)
					backupFile.value = _clone(currentFile.value)
					message.success("Detection rules uploaded Successfully")
				} else {
					message.error("An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				uploadingFile.value = false
			})
	}
}

watch(
	[filters],
	() => {
		pagination.value.current = 1
	},
	{ deep: true }
)

watchDebounced(
	[filters, () => pagination.value.current],
	() => {
		getList()
	},
	{ debounce: 250, immediate: true, deep: true }
)
</script>
