<template>
	<div class="soc-case-item" :class="{ embedded }">
		<div class="flex flex-col gap-2 px-5 py-3">
			<div class="header-box flex justify-between">
				<div class="flex items-center gap-2">
					<div class="id flex items-center gap-2 cursor-pointer" @click="showDetails = true">
						<span>{{ caseData.case_uuid }}</span>
						<Icon :name="InfoIcon" :size="16"></Icon>
					</div>
				</div>
				<div class="time">
					<n-popover overlap placement="top-end">
						<template #trigger>
							<div class="flex items-center gap-2 cursor-help">
								<span>
									{{ formatDate(caseData.case_open_date) }}
								</span>
								<Icon :name="TimeIcon" :size="16"></Icon>
							</div>
						</template>
						<div class="flex flex-col py-2 px-1">
							<n-timeline>
								<n-timeline-item
									type="success"
									:title="`Open [${caseData.opened_by}]`"
									:time="formatDate(caseData.case_open_date)"
								/>
								<n-timeline-item
									v-if="caseData.case_close_date"
									title="Close date"
									:time="formatDate(caseData.case_close_date)"
								/>
							</n-timeline>
						</div>
					</n-popover>
				</div>
			</div>
			<div class="main-box flex justify-between gap-4">
				<div class="content">
					<div class="title" v-html="caseData.case_name"></div>
					<div class="description mt-2" v-if="caseData.case_description">{{ excerpt }}</div>

					<div class="badges-box flex flex-wrap items-center gap-3 mt-4">
						<Badge type="splitted" :color="caseData.state_name === StateName.Open ? 'warning' : undefined">
							<template #iconLeft>
								<Icon :name="StatusIcon" :size="14"></Icon>
							</template>
							<template #label>State</template>
							<template #value>{{ caseData.state_name }}</template>
						</Badge>
						<Badge type="splitted">
							<template #iconLeft>
								<Icon :name="OwnerIcon" :size="16"></Icon>
							</template>
							<template #label>Owner</template>
							<template #value>{{ caseData.owner }}</template>
						</Badge>
						<Badge type="splitted">
							<template #iconLeft>
								<Icon :name="CustomerIcon" :size="13"></Icon>
							</template>
							<template #label>Client</template>
							<template #value>{{ caseData.client_name || "-" }}</template>
						</Badge>
						<Badge
							v-if="caseData.case_soc_id"
							type="active"
							@click="gotoSocAlert(caseData.case_soc_id)"
							class="cursor-pointer"
						>
							<template #iconRight>
								<Icon :name="LinkIcon" :size="14"></Icon>
							</template>
							<template #label>Alert #{{ caseData.case_soc_id }}</template>
						</Badge>
					</div>
				</div>
			</div>
			<div class="footer-box flex justify-end items-center gap-3">
				<div class="time">{{ formatDate(caseData.case_open_date) }}</div>
			</div>
		</div>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-style="padding:0px"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(550px, 90vh)', overflow: 'hidden' }"
			:title="caseData.case_uuid"
			:bordered="false"
			segmented
		>
			<n-tabs type="line" animated justify-content="space-evenly">
				<n-tab-pane name="Info" tab="Info" display-directive="show">
					<n-spin :show="loadingDetails">
						<div class="px-7 py-4" v-if="extendedInfo">
							<div class="flex gap-2 mb-2" v-if="tags.length">
								<code v-for="tag of tags" :key="tag">{{ tag }}</code>
							</div>
							<div>{{ extendedInfo.case_name }}</div>
						</div>
						<div class="flex flex-col gap-2 px-7 py-4" v-if="extendedInfo">
							<div class="box">
								soc id:
								<code
									class="cursor-pointer text-primary-color"
									@click="gotoSocAlert(caseData.case_soc_id)"
								>
									#{{ caseData.case_soc_id }}
									<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
								</code>
							</div>
							<div class="box" v-if="extendedInfo?.protagonists && extendedInfo?.protagonists.length">
								protagonists:
								<code v-for="protagonist of extendedInfo.protagonists" :key="protagonist" class="mr-2">
									{{ protagonist }}
								</code>
							</div>
						</div>
						<div class="grid gap-2 soc-case-context-grid p-7 pt-4" v-if="properties">
							<KVCard v-for="(value, key) of properties" :key="key">
								<template #key>{{ key }}</template>
								<template #value>{{ value || "-" }}</template>
							</KVCard>
						</div>
					</n-spin>
				</n-tab-pane>
				<n-tab-pane name="Description" tab="Description" display-directive="show">
					<div class="p-7 pt-4">
						<n-input
							:value="caseData.case_description"
							type="textarea"
							readonly
							placeholder="Empty"
							:autosize="{
								minRows: 3,
								maxRows: 10
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
					<SocCaseAssetsList :case-id="caseData.case_id" />
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
										:case-id="caseData.case_id"
										@close="noteFormVisible = []"
										@added="updateNotes = true"
									/>
								</div>
							</n-collapse-item>
						</n-collapse>
					</div>
					<n-divider class="!my-2" />
					<SocCaseNotesList :case-id="caseData.case_id" v-model:requested="updateNotes" />
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import KVCard from "@/components/common/KVCard.vue"
import Badge from "@/components/common/Badge.vue"
import { computed, ref, watch } from "vue"
import SocCaseTimeline from "./SocCaseTimeline.vue"
import SocCaseAssetsList from "./SocCaseAssetsList.vue"
import SocCaseNoteForm from "./SocCaseNoteForm.vue"
import SocCaseNotesList from "./SocCaseNotesList.vue"
import "@/assets/scss/vuesjv-override.scss"
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
import { useRouter } from "vue-router"

const { caseData, embedded } = defineProps<{ caseData: SocCase; embedded?: boolean }>()

const TimeIcon = "carbon:time"
const InfoIcon = "carbon:information"
const CustomerIcon = "carbon:user"
const LinkIcon = "carbon:launch"
const OwnerIcon = "carbon:user-military"
const StatusIcon = "fluent:status-20-regular"
const AddIcon = "carbon:add-alt"

const showDetails = ref(false)
const loadingDetails = ref(false)
const message = useMessage()
const router = useRouter()
const noteFormVisible = ref([])
const updateNotes = ref(false)

const extendedInfo = ref<SocCaseExt | null>(null)

const dFormats = useSettingsStore().dateFormat

const excerpt = computed(() => {
	const text = caseData.case_description
	const truncated = text.split(" ").slice(0, 30).join(" ")

	return truncated + (truncated !== text ? "..." : "")
})

const tags = computed<string[]>(() => {
	if (!extendedInfo?.value?.case_tags) {
		return []
	}

	return _split(extendedInfo.value?.case_tags, ",").map(o => "#" + o)
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

function gotoSocAlert(socId: string) {
	router.push(`/soc/alerts?id=${socId}`).catch(() => {})
}

function getDetails() {
	loadingDetails.value = true

	Api.soc
		.getCases(caseData.case_id.toString())
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

watch(showDetails, val => {
	if (val && !extendedInfo.value) {
		getDetails()
	}
})
</script>

<style lang="scss" scoped>
.soc-case-item {
	&:not(.embedded) {
		border-radius: var(--border-radius);
		background-color: var(--bg-color);
		border: var(--border-small-050);
	}
	border-top: var(--border-small-050);
	transition: all 0.2s var(--bezier-ease);

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
		font-family: var(--font-family-mono);
		font-size: 13px;
		margin-top: 10px;
		display: none;

		.time {
			text-align: right;
			color: var(--fg-secondary-color);
		}
	}

	&:not(.embedded) {
		&:hover {
			box-shadow: 0px 0px 0px 1px inset var(--primary-color);
		}
	}

	@container (max-width: 650px) {
		.header-box {
			.time {
				display: none;
			}
		}
		.footer-box {
			display: flex;
		}
	}
}
</style>
<style lang="scss">
.soc-case-context-grid {
	grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
	grid-auto-flow: row dense;
}
</style>
