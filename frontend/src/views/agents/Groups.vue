<template>
	<div class="page page-wrapped page-mobile-full page-without-footer flex flex-col">
		<SegmentedPage
			main-content-class="p-0! overflow-hidden grow flex flex-col h-full"
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
						placeholder="Search groups..."
					>
						<template #prefix>
							<Icon :name="SearchIcon" :size="16" />
						</template>
					</n-input>

					<n-tooltip>
						<template #trigger>
							<n-button secondary :loading="loadingRefresh" size="small" @click="refreshGroups()">
								<template #icon>
									<Icon :name="RefreshIcon" />
								</template>
							</n-button>
						</template>
						<div>Refresh Groups</div>
					</n-tooltip>
				</div>
			</template>
			<template #sidebar-content>
				<n-spin :show="loadingGroups">
					<template v-if="groupsList.length">
						<div class="divide-border flex flex-col divide-y">
							<div
								v-for="group of groupsList"
								:key="group.name"
								class="hover:text-warning cursor-pointer px-4.5 py-2.5 text-sm break-all"
								:class="{ 'bg-warning/10': group.name === currentGroup?.name }"
								@click.stop="loadGroup(group)"
							>
								<div class="font-mono">{{ group.name }}</div>
								<div class="text-secondary text-xs">{{ group.count }} agents</div>
							</div>
						</div>
					</template>
					<template v-else>
						<n-empty v-if="!loadingGroups" description="No groups found" class="h-48 justify-center" />
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
			<template v-if="currentGroup && currentFile" #main-toolbar>
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
							:loading="uploadingConfig"
							size="small"
							type="primary"
							:disabled="!isDirty"
							@click="updateGroupConfiguration()"
						>
							<div class="flex items-center gap-2">
								<Icon :name="UploadIcon" />
								<span class="hidden @xs:flex">Update</span>
							</div>
						</n-button>
					</div>
				</div>
			</template>
			<template #main-content>
				<div v-if="currentGroup && currentFile" class="px-4.5 py-2.5 text-sm break-all">
					<div class="font-mono">Group: {{ currentGroup?.name }} | File: {{ currentFile?.filename }}</div>
				</div>
				<n-spin
					:show="loadingFile || uploadingConfig"
					class="flex h-full w-full overflow-hidden"
					content-class="flex h-full grow flex-col justify-center overflow-hidden"
				>
					<template v-if="currentGroup && currentFile">
						<XMLEditor
							v-model="currentFile.content"
							class="scrollbar-styled text-sm"
							@errors="xmlErrors = $event"
							@mounted="xmlEditorCTX = $event"
						/>
					</template>
					<template v-else>
						<n-empty v-if="!loadingFile" description="Select a group" class="h-48 justify-center" />
					</template>
				</n-spin>
			</template>
		</SegmentedPage>
	</div>
</template>

<script setup lang="ts">
import type { XMLEditorCtx, XMLError } from "@/components/common/XMLEditor.vue"
import type { WazuhGroup, WazuhGroupFileDetails } from "@/types/wazuh/groups.d"
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
const loadingRefresh = ref(false)
const loadingGroups = ref(false)
const loadingFile = ref(false)
const uploadingConfig = ref(false)
const groupsList = ref<WazuhGroup[]>([])
const currentGroup = ref<WazuhGroup | null>(null)
const currentFile = ref<WazuhGroupFileDetails | null>(null)
const backupFile = ref<WazuhGroupFileDetails | null>(null)
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

function loadGroup(group: WazuhGroup) {
	if (group.name !== currentGroup.value?.name) {
		currentGroup.value = group
		// Auto-load agent.conf file when a group is selected
		loadGroupFile(group.name, "agent.conf")
	}
}

function refreshGroups() {
	abortController?.abort()
	loadingRefresh.value = true
	getGroups().finally(() => {
		loadingRefresh.value = false
	})
}

function getGroups() {
	abortController?.abort()
	abortController = new AbortController()

	loadingGroups.value = true

	return Api.wazuh.groups
		.getGroups(
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
				groupsList.value = res.data.results || []
				pagination.value.total = res.data.total_items
			} else {
				pagination.value.total = 0
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
			loadingGroups.value = false
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				groupsList.value = []
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
				loadingGroups.value = false
			}
		})
}

function loadGroupFile(groupId: string, filename: string) {
	loadingFile.value = true

	Api.wazuh.groups
		.getGroupFile(groupId, filename)
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

function updateGroupConfiguration() {
	if (currentGroup.value && currentFile.value) {
		uploadingConfig.value = true

		Api.wazuh.groups
			.updateGroupConfiguration(currentGroup.value.name, currentFile.value.content)
			.then(res => {
				if (res.data.success) {
					currentFile.value = _clone(currentFile.value)
					backupFile.value = _clone(currentFile.value)
					message.success("Group configuration updated successfully")
				} else {
					message.error("An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				uploadingConfig.value = false
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
		getGroups()
	},
	{ debounce: 250, immediate: true, deep: true }
)
</script>
