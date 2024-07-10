<template>
	<n-spin
		:show="loadingDetails || loadingDelete"
		:description="loadingDelete ? 'Deleting Soc Case' : 'Loading Soc Case'"
	>
		<div class="soc-case-item" :class="{ embedded }">
			<div class="flex flex-col gap-2 px-5 py-3" v-if="baseInfo">
				<div class="header-box flex justify-between">
					<div class="flex items-center gap-2">
						<div class="id flex items-center gap-2 cursor-pointer" @click="showDetails = true">
							<span>{{ baseInfo.case_uuid }}</span>
							<Icon :name="InfoIcon" :size="16"></Icon>
						</div>
					</div>
					<div class="time" v-if="caseOpenDate">
						<n-popover overlap placement="top-end">
							<template #trigger>
								<div class="flex items-center gap-2 cursor-help">
									<span>
										{{ formatDate(caseOpenDate) }}
									</span>
									<Icon :name="TimeIcon" :size="16"></Icon>
								</div>
							</template>
							<div class="flex flex-col py-2 px-1">
								<n-timeline>
									<n-timeline-item
										type="success"
										:title="`Open ${openedBy ? '[' + openedBy + ']' : ''}`"
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
					</div>
				</div>
				<div class="main-box flex items-center justify-between gap-4">
					<div class="content">
						<div class="title" v-html="baseInfo.case_name"></div>
						<div class="description mt-2" v-if="baseInfo.case_description">{{ excerpt }}</div>

						<div class="badges-box flex flex-wrap items-center gap-3 mt-4">
							<Badge
								type="splitted"
								:color="baseInfo.state_name === StateName.Open ? 'warning' : undefined"
							>
								<template #iconLeft>
									<Icon :name="StatusIcon" :size="14"></Icon>
								</template>
								<template #label>State</template>
								<template #value>{{ baseInfo.state_name }}</template>
							</Badge>
							<Badge type="splitted">
								<template #iconLeft>
									<Icon :name="OwnerIcon" :size="16"></Icon>
								</template>
								<template #label>Owner</template>
								<template #value>{{ baseInfo.owner }}</template>
							</Badge>
							<Badge type="splitted">
								<template #iconLeft>
									<Icon :name="CustomerIcon" :size="13"></Icon>
								</template>
								<template #label>Client</template>
								<template #value>{{ clientName || "-" }}</template>
							</Badge>
							<Badge
								v-if="baseInfo.case_soc_id && !hideSocAlertLink"
								type="active"
								@click="openSocAlert()"
								class="cursor-pointer"
							>
								<template #iconRight>
									<Icon :name="LinkIcon" :size="14"></Icon>
								</template>
								<template #label>Alert #{{ baseInfo.case_soc_id }}</template>
							</Badge>
						</div>
					</div>
					<SocCaseItemActions
						v-if="!hideSocCaseAction"
						class="actions-box"
						:caseData="baseInfo"
						@closed="setClosed()"
						@reopened="setReopened()"
						@deleted="deleteCase()"
						@startDeleting="loadingDelete = true"
					/>
				</div>
				<div class="footer-box flex justify-between items-center gap-3">
					<SocCaseItemActions
						v-if="!hideSocCaseAction"
						class="actions-box !flex-row"
						:caseData="baseInfo"
						:size="'small'"
						@closed="setClosed()"
						@reopened="setReopened()"
						@deleted="deleteCase()"
						@startDeleting="loadingDelete = true"
					/>
					<div class="time" v-if="caseOpenDate">{{ formatDate(caseOpenDate) }}</div>
				</div>
			</div>

			<n-modal
				v-model:show="showSocAlertDetails"
				preset="card"
				content-class="!p-0"
				:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(250px, 90vh)', overflow: 'hidden' }"
				:title="`SOC Alert: #${baseInfo?.case_soc_id}`"
				:bordered="false"
				segmented
			>
				<div class="h-full w-full flex items-center justify-center">
					<SocAlertItem
						v-if="baseInfo?.case_soc_id"
						:alertId="baseInfo.case_soc_id"
						embedded
						hideBookmarkAction
						hideSocCaseAction
						class="w-full"
					/>
				</div>
			</n-modal>

			<n-modal
				v-model:show="showDetails"
				preset="card"
				content-class="!p-0"
				:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(550px, 90vh)', overflow: 'hidden' }"
				:title="'SOC Case: ' + baseInfo?.case_uuid"
				:bordered="false"
				segmented
			>
				<n-tabs type="line" animated :tabs-padding="24">
					<n-tab-pane name="Info" tab="Info" display-directive="show">
						<n-spin :show="loadingDetails">
							<div class="px-7 py-4" v-if="extendedInfo">
								<div class="flex gap-2 mb-2" v-if="tags.length">
									<code v-for="tag of tags" :key="tag">{{ tag }}</code>
								</div>
								<div>{{ extendedInfo.case_name }}</div>
							</div>
							<div class="flex flex-col gap-2 px-7 py-4" v-if="extendedInfo">
								<div class="box" v-if="baseInfo && !hideSocAlertLink">
									soc id:
									<code class="cursor-pointer text-primary-color" @click="openSocAlert()">
										#{{ baseInfo.case_soc_id }}
										<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
									</code>
								</div>
								<div class="box" v-if="extendedInfo?.protagonists && extendedInfo?.protagonists.length">
									protagonists:
									<code
										v-for="protagonist of extendedInfo.protagonists"
										:key="protagonist"
										class="mr-2"
									>
										{{ protagonist }}
									</code>
								</div>
							</div>
							<div class="grid gap-2 grid-auto-flow-200 p-7 pt-4" v-if="properties">
								<KVCard v-for="(value, key) of properties" :key="key">
									<template #key>{{ key }}</template>
									<template #value>
										<template
											v-if="key === 'customer_code' && value && value !== 'Customer Not Found'"
										>
											<code
												class="cursor-pointer text-primary-color"
												@click="gotoCustomer({ code: value })"
											>
												#{{ value }}
												<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
											</code>
										</template>
										<template v-else>
											{{ value || "-" }}
										</template>
									</template>
								</KVCard>
							</div>
						</n-spin>
					</n-tab-pane>
					<n-tab-pane name="Description" tab="Description" display-directive="show">
						<div class="p-7 pt-4" v-if="baseInfo">
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
								<SocCaseTimeline :caseData="extendedInfo" v-if="extendedInfo" />
							</div>
						</n-spin>
					</n-tab-pane>
					<n-tab-pane name="Assets" tab="Assets" display-directive="show:lazy">
						<SocCaseAssetsList v-if="baseInfo" :case-id="baseInfo.case_id" />
					</n-tab-pane>
					<n-tab-pane name="Notes" tab="Notes" display-directive="show:lazy">
						<div class="px-4">
							<n-collapse display-directive="show" v-model:expanded-names="noteFormVisible">
								<template #arrow>
									<div class="mx-4 flex">
										<Icon :name="AddIcon"></Icon>
									</div>
								</template>
								<n-collapse-item name="1">
									<template #header>
										<div class="py-3 -ml-2">New note</div>
									</template>
									<div class="p-3 pt-0 -mt-2">
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
						<SocCaseNotesList v-if="baseInfo" :case-id="baseInfo.case_id" v-model:requested="updateNotes" />
					</n-tab-pane>
				</n-tabs>
			</n-modal>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import KVCard from "@/components/common/KVCard.vue"
import Badge from "@/components/common/Badge.vue"
import { computed, onBeforeMount, ref, watch } from "vue"
import SocCaseTimeline from "./SocCaseTimeline.vue"
import SocCaseAssetsList from "./SocCaseAssetsList.vue"
import SocCaseNoteForm from "./SocCaseNoteForm.vue"
import SocCaseNotesList from "./SocCaseNotesList.vue"
import SocCaseItemActions from "./SocCaseItemActions.vue"
import SocAlertItem from "../SocAlerts/SocAlertItem/SocAlertItem.vue"
import Api from "@/api"
import {
	useMessage,
	NPopover,
	NSpin,
	NTimeline,
	NTimelineItem,
	NModal,
	NTabs,
	NTabPane,
	NDivider,
	NInput,
	NCollapse,
	NCollapseItem
} from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import { type SocCase, StateName, type SocCaseExt } from "@/types/soc/case.d"
import _omit from "lodash/omit"
import _split from "lodash/split"
import { useGoto } from "@/composables/useGoto"

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

const TimeIcon = "carbon:time"
const InfoIcon = "carbon:information"
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

const baseInfo = computed<SocCase | SocCaseExt | null>(() => caseData || extendedInfo.value)
const extendedInfo = ref<SocCaseExt | null>(null)

const dFormats = useSettingsStore().dateFormat

const caseOpenDate = computed<string | null>(() => {
	if (baseInfo.value && "case_open_date" in baseInfo.value) {
		return baseInfo.value.case_open_date as string
	}
	if (baseInfo.value && "open_date" in baseInfo.value) {
		return baseInfo.value.open_date as string
	}
	if (extendedInfo.value && "open_date" in extendedInfo.value) {
		return extendedInfo.value.open_date as string
	}
	return null
})

const caseCloseDate = computed<string | null>(() => {
	if (baseInfo.value && "case_close_date" in baseInfo.value) {
		return baseInfo.value.case_close_date as string
	}
	if (baseInfo.value && "close_date" in baseInfo.value) {
		return baseInfo.value.close_date as string
	}
	if (extendedInfo.value && "close_date" in extendedInfo.value) {
		return extendedInfo.value.close_date as string
	}
	return null
})

const clientName = computed<string | null>(() => {
	if (baseInfo.value && "client_name" in baseInfo.value) {
		return baseInfo.value.client_name as string
	}
	return null
})

const openedBy = computed<string | null>(() => {
	if (baseInfo.value && "opened_by" in baseInfo.value) {
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

<style lang="scss" scoped>
.soc-case-item {
	border-top: var(--border-small-050);
	transition: all 0.2s var(--bezier-ease);
	min-height: 100px;

	.header-box {
		font-family: var(--font-family-mono);
		font-size: 13px;
		.id {
			word-break: break-word;
			color: var(--fg-secondary-color);
			line-height: 1.2;

			&:hover {
				color: var(--primary-color);
			}
		}

		.toggler-bookmark {
			&.active {
				color: var(--primary-color);
			}
			&:hover {
				color: var(--primary-color);
			}
		}
		.time {
			color: var(--fg-secondary-color);

			&:hover {
				color: var(--primary-color);
			}
		}
	}

	.main-box {
		word-break: break-word;

		.description {
			color: var(--fg-secondary-color);
			font-size: 13px;
		}
	}

	.footer-box {
		font-size: 13px;
		margin-top: 10px;
		display: none;

		.time {
			text-align: right;
			font-family: var(--font-family-mono);
			color: var(--fg-secondary-color);
		}
	}

	&:not(.embedded) {
		border-radius: var(--border-radius);
		background-color: var(--bg-color);
		border: var(--border-small-050);

		&:hover {
			border-color: var(--primary-color);
		}
	}

	@container (max-width: 650px) {
		.header-box {
			.time {
				display: none;
			}
		}

		.main-box {
			.actions-box {
				display: none;
			}
		}

		.footer-box {
			display: flex;
		}
	}
}
</style>
