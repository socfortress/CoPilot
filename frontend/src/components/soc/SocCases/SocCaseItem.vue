<template>
	<div>
		<CardEntity
			:loading="loadingDetails || loadingDelete"
			:loading-description="loadingDelete ? 'Deleting Soc Case' : 'Loading Soc Case'"
			:embedded
			hoverable
			clickable
			@click.stop="showDetails = true"
		>
			<template #headerMain>{{ baseInfo?.case_uuid }}</template>
			<template v-if="caseOpenDate" #headerExtra>
				<n-popover overlap placement="top-end">
					<template #trigger>
						<div class="hover:text-primary flex cursor-help items-center gap-2">
							<span>
								{{ formatDate(caseOpenDate) }}
							</span>
							<Icon :name="TimeIcon" :size="16"></Icon>
						</div>
					</template>
					<div class="flex flex-col px-1 py-2">
						<n-timeline>
							<n-timeline-item
								type="success"
								:title="`Open ${openedBy ? `[${openedBy}]` : ''}`"
								:time="formatDate(caseOpenDate)"
							/>
							<n-timeline-item
								v-if="caseCloseDate"
								title="Close date"
								:time="formatDate(caseCloseDate)"
							/>
						</n-timeline>
					</div>
				</n-popover>
			</template>
			<template #default>
				<div class="flex flex-col gap-1">
					<div v-html="baseInfo?.case_name"></div>
					<p v-if="baseInfo?.case_description">
						{{ excerpt }}
					</p>
				</div>
			</template>
			<template v-if="baseInfo" #mainExtra>
				<div class="flex flex-wrap items-center gap-3">
					<Badge type="splitted" :color="baseInfo.state_name === StateName.Open ? 'warning' : 'primary'">
						<template #iconLeft>
							<Icon :name="StatusIcon" :size="14"></Icon>
						</template>
						<template #label>State</template>
						<template #value>
							{{ baseInfo.state_name }}
						</template>
					</Badge>
					<Badge type="splitted" color="primary">
						<template #iconLeft>
							<Icon :name="OwnerIcon" :size="16"></Icon>
						</template>
						<template #label>Owner</template>
						<template #value>
							{{ baseInfo.owner }}
						</template>
					</Badge>
					<Badge type="splitted" color="primary">
						<template #iconLeft>
							<Icon :name="CustomerIcon" :size="13"></Icon>
						</template>
						<template #label>Client</template>
						<template #value>
							{{ clientName || "-" }}
						</template>
					</Badge>
					<Badge
						v-if="baseInfo.case_soc_id && !hideSocAlertLink"
						type="active"
						class="cursor-pointer"
						@click.stop="openSocAlert()"
					>
						<template #iconRight>
							<Icon :name="LinkIcon" :size="14"></Icon>
						</template>
						<template #label>Alert #{{ baseInfo.case_soc_id }}</template>
					</Badge>
				</div>
			</template>
			<template #footerExtra>
				<SocCaseItemActions
					v-if="!hideSocCaseAction"
					class="flex flex-col justify-center gap-2"
					:case-data="baseInfo"
					size="small"
					@closed="setClosed()"
					@reopened="setReopened()"
					@deleted="deleteCase()"
					@start-deleting="loadingDelete = true"
				/>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showSocAlertDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(250px, 90vh)', overflow: 'hidden' }"
			:title="`SOC Alert: #${baseInfo?.case_soc_id}`"
			:bordered="false"
			segmented
		>
			<div class="flex h-full w-full items-center justify-center">
				<SocAlertItem
					v-if="baseInfo?.case_soc_id"
					:alert-id="baseInfo.case_soc_id"
					embedded
					hide-bookmark-action
					hide-soc-case-action
					class="w-full"
				/>
			</div>
		</n-modal>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(550px, 90vh)', overflow: 'hidden' }"
			:title="`SOC Case: ${baseInfo?.case_uuid}`"
			:bordered="false"
			segmented
		>
			<n-tabs type="line" animated :tabs-padding="24">
				<n-tab-pane name="Info" tab="Info" display-directive="show">
					<n-spin :show="loadingDetails">
						<div v-if="extendedInfo" class="px-7 py-4">
							<div v-if="tags.length" class="mb-2 flex gap-2">
								<code v-for="tag of tags" :key="tag">{{ tag }}</code>
							</div>
							<div>{{ extendedInfo.case_name }}</div>
						</div>
						<div v-if="extendedInfo" class="flex flex-col gap-2 px-7 py-4">
							<div v-if="baseInfo && !hideSocAlertLink" class="box">
								soc id:
								<code class="text-primary cursor-pointer" @click.stop="openSocAlert()">
									#{{ baseInfo.case_soc_id }}
									<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
								</code>
							</div>
							<div v-if="extendedInfo?.protagonists && extendedInfo?.protagonists.length" class="box">
								protagonists:
								<code v-for="protagonist of extendedInfo.protagonists" :key="protagonist" class="mr-2">
									{{ protagonist }}
								</code>
							</div>
						</div>
						<div v-if="properties" class="grid-auto-fit-200 grid gap-2 p-7 pt-4">
							<CardKV v-for="(value, key) of properties" :key="key">
								<template #key>
									{{ key }}
								</template>
								<template #value>
									<template v-if="key === 'customer_code' && value && value !== 'Customer Not Found'">
										<code
											class="text-primary cursor-pointer"
											@click.stop="gotoCustomer({ code: value })"
										>
											#{{ value }}
											<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
										</code>
									</template>
									<template v-else>
										{{ value || "-" }}
									</template>
								</template>
							</CardKV>
						</div>
					</n-spin>
				</n-tab-pane>
				<n-tab-pane name="Description" tab="Description" display-directive="show">
					<div v-if="baseInfo" class="p-7 pt-4">
						<n-input
							:value="baseInfo.case_description"
							type="textarea"
							readonly
							placeholder="Empty"
							size="large"
							:autosize="{
								minRows: 3
							}"
						/>
					</div>
				</n-tab-pane>
				<n-tab-pane name="History" tab="History" display-directive="show:lazy">
					<n-spin :show="loadingDetails">
						<div class="p-7 pt-4">
							<SocCaseTimeline v-if="extendedInfo" :case-data="extendedInfo" />
						</div>
					</n-spin>
				</n-tab-pane>
				<n-tab-pane name="Assets" tab="Assets" display-directive="show:lazy">
					<SocCaseAssetsList v-if="baseInfo" :case-id="baseInfo.case_id" />
				</n-tab-pane>
				<n-tab-pane name="Notes" tab="Notes" display-directive="show:lazy">
					<div class="px-4">
						<n-collapse v-model:expanded-names="noteFormVisible" display-directive="show">
							<template #arrow>
								<div class="mx-4 flex">
									<Icon :name="AddIcon"></Icon>
								</div>
							</template>
							<n-collapse-item name="1">
								<template #header>
									<div class="-ml-2 py-3">New note</div>
								</template>
								<div class="-mt-2 p-3 pt-0">
									<SocCaseNoteForm
										v-if="baseInfo"
										:case-id="baseInfo.case_id"
										@close="noteFormVisible = []"
										@added="updateNotes = true"
									/>
								</div>
							</n-collapse-item>
						</n-collapse>
					</div>
					<n-divider class="!my-2" />
					<SocCaseNotesList v-if="baseInfo" v-model:requested="updateNotes" :case-id="baseInfo.case_id" />
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { SocCase, SocCaseExt } from "@/types/soc/case.d"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import { useSettingsStore } from "@/stores/settings"
import { StateName } from "@/types/soc/case.d"
import dayjs from "@/utils/dayjs"
import _omit from "lodash/omit"
import _split from "lodash/split"
import {
	NCollapse,
	NCollapseItem,
	NDivider,
	NInput,
	NModal,
	NPopover,
	NSpin,
	NTabPane,
	NTabs,
	NTimeline,
	NTimelineItem,
	useMessage
} from "naive-ui"
import { computed, defineAsyncComponent, onBeforeMount, ref, watch } from "vue"

const { caseData, caseId, embedded, hideSocCaseAction, hideSocAlertLink } = defineProps<{
	caseData?: SocCase
	caseId?: number | string
	embedded?: boolean
	hideSocAlertLink?: boolean
	hideSocCaseAction?: boolean
}>()
const emit = defineEmits<{
	(e: "deleted"): void
}>()
const SocCaseTimeline = defineAsyncComponent(() => import("./SocCaseTimeline.vue"))
const SocCaseAssetsList = defineAsyncComponent(() => import("./SocCaseAssetsList.vue"))
const SocCaseNoteForm = defineAsyncComponent(() => import("./SocCaseNoteForm.vue"))
const SocCaseNotesList = defineAsyncComponent(() => import("./SocCaseNotesList.vue"))
const SocCaseItemActions = defineAsyncComponent(() => import("./SocCaseItemActions.vue"))
const SocAlertItem = defineAsyncComponent(() => import("../SocAlerts/SocAlertItem/SocAlertItem.vue"))

const TimeIcon = "carbon:time"
const CustomerIcon = "carbon:user"
const LinkIcon = "carbon:launch"
const OwnerIcon = "carbon:user-military"
const StatusIcon = "fluent:status-20-regular"
const AddIcon = "carbon:add-alt"

const { gotoCustomer } = useGoto()
const showSocAlertDetails = ref(false)
const showDetails = ref(false)
const loadingDetails = ref(false)
const loadingDelete = ref(false)
const message = useMessage()
const noteFormVisible = ref([])
const updateNotes = ref(false)

const extendedInfo = ref<SocCaseExt | null>(null)
const baseInfo = computed<(SocCase & Partial<SocCaseExt>) | null>(() => {
	if (caseData) {
		return { ...caseData, ...(extendedInfo.value || {}) }
	}
	return null
})

const dFormats = useSettingsStore().dateFormat

const caseOpenDate = computed<string | null>(() => {
	if (baseInfo.value?.case_open_date) {
		return baseInfo.value.case_open_date as string
	}
	if (baseInfo.value?.open_date) {
		return baseInfo.value.open_date as string
	}
	if (extendedInfo.value?.open_date) {
		return extendedInfo.value.open_date as string
	}
	return null
})

const caseCloseDate = computed<string | null>(() => {
	if (baseInfo.value?.case_close_date) {
		return baseInfo.value.case_close_date as string
	}
	if (baseInfo.value?.close_date) {
		return baseInfo.value.close_date as string
	}
	if (extendedInfo.value?.close_date) {
		return extendedInfo.value.close_date as string
	}
	return null
})

const clientName = computed<string | null>(() => {
	if (baseInfo.value?.client_name) {
		return baseInfo.value.client_name as string
	}
	return null
})

const openedBy = computed<string | null>(() => {
	if (baseInfo.value?.opened_by) {
		return baseInfo.value.opened_by as string
	}
	return null
})

const excerpt = computed(() => {
	const text = caseData?.case_description || ""
	const truncated = text.split(" ").slice(0, 30).join(" ")

	return truncated + (truncated !== text ? "..." : "")
})

const tags = computed<string[]>(() => {
	if (!extendedInfo?.value?.case_tags) {
		return []
	}

	return _split(extendedInfo.value?.case_tags, ",")
})

const properties = computed(() => {
	return _omit(extendedInfo.value, [
		"case_description",
		"case_name",
		"case_soc_id",
		"case_tags",
		"case_uuid",
		"close_date",
		"initial_date",
		"modification_history",
		"open_by_user",
		"open_by_user_id",
		"open_date",
		"protagonists"
	])
})

function formatDate(timestamp: string | number | Date, utc: boolean = true): string {
	return dayjs(timestamp).utc(utc).format(dFormats.date)
}

function setClosed() {
	if (baseInfo.value) {
		baseInfo.value.state_name = StateName.Closed
	}
}

function setReopened() {
	if (baseInfo.value) {
		baseInfo.value.state_name = StateName.Open
	}
}

function deleteCase() {
	loadingDelete.value = false
	emit("deleted")
}

function openSocAlert() {
	showSocAlertDetails.value = true
}

function getDetails() {
	if (caseId || baseInfo.value) {
		loadingDetails.value = true

		Api.soc
			.getCases(caseId?.toString() || baseInfo.value?.case_id.toString())
			.then(res => {
				if (res.data.success) {
					extendedInfo.value = res.data?.case || null
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				loadingDetails.value = false
			})
	}
}

watch(showDetails, val => {
	if (val && !extendedInfo.value) {
		getDetails()
	}
})

onBeforeMount(() => {
	if (!caseData && caseId) {
		getDetails()
	}
})
</script>
