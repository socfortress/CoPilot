<template>
	<div class="soc-case-note">
		<div class="flex flex-col gap-2 px-5 py-4">
			<div class="header-box flex justify-between">
				<div class="flex items-center gap-2">
					<div class="id flex items-center gap-2 cursor-pointer" @click="showDetails = true">
						<span>#{{ note.note_id }} - {{ note.note_details.note_uuid }}</span>
						<Icon :name="InfoIcon" :size="16"></Icon>
					</div>
				</div>
				<div class="time">
					<n-popover overlap placement="top-end">
						<template #trigger>
							<div class="flex items-center gap-2 cursor-help">
								<span>
									{{ formatDateTime(note.note_details.note_creationdate) }}
								</span>
								<Icon :name="TimeIcon" :size="16"></Icon>
							</div>
						</template>
						<div class="flex flex-col py-2 px-1">
							<SocCaseNoteTimeline :note="note" />
						</div>
					</n-popover>
				</div>
			</div>
			<div class="main-box flex justify-between gap-4">
				<div class="content">
					<div class="title" v-html="note.note_title"></div>
					<div class="description mt-2" v-if="note.note_details.note_content">{{ excerpt }}</div>

					<!--
						<div class="badges-box flex flex-wrap items-center gap-3 mt-4">
							<Badge type="splitted">
								<template #label>Status</template>
								<template #value>{{ asset.analysis_status }}</template>
							</Badge>
							<Badge type="splitted">
								<template #label>Type</template>
								<template #value>{{ asset.asset_type }}</template>
							</Badge>
							<Badge type="splitted" v-for="tag of tags" :key="tag.key">
								<template #label>{{ tag.key }}</template>
								<template #value v-if="tag.value !== undefined">{{ tag.value || "-" }}</template>
							</Badge>
						</div>
					-->
				</div>
			</div>
			<div class="footer-box flex justify-end items-center gap-3">
				<div class="time">{{ formatDateTime(note.note_details.note_creationdate) }}</div>
			</div>
		</div>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			:title="`Note: #${note.note_id} - ${note.note_details.note_uuid}`"
			:bordered="false"
			segmented
		>
			<n-tabs type="line" animated :tabs-padding="24">
				<n-tab-pane name="Info" tab="Info" display-directive="show">
					<div class="grid gap-2 grid-auto-flow-200 p-7 pt-4" v-if="properties">
						<KVCard v-for="(value, key) of properties" :key="key">
							<template #key>{{ key }}</template>
							<template #value>{{ value || "-" }}</template>
						</KVCard>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Content" tab="Content" display-directive="show">
					<div class="p-7 pt-4">
						<n-input
							:value="note.note_details.note_content"
							type="textarea"
							readonly
							placeholder="Empty"
							size="large"
							:autosize="{
								minRows: 3,
								maxRows: 10
							}"
						/>
					</div>
				</n-tab-pane>
				<n-tab-pane name="History" tab="History" display-directive="show:lazy">
					<div class="p-7 pt-4">
						<SocCaseNoteTimeline :note="note" />
					</div>
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import KVCard from "@/components/common/KVCard.vue"
import SocCaseNoteTimeline from "./SocCaseNoteTimeline.vue"
import { computed, ref } from "vue"
import { NModal, NTabs, NTabPane, NInput, NPopover } from "naive-ui"
import _omit from "lodash/omit"
import type { SocNote } from "@/types/soc/note.d"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"

const { note } = defineProps<{ note: SocNote }>()

const InfoIcon = "carbon:information"
const TimeIcon = "carbon:time"

const showDetails = ref(false)
const dFormats = useSettingsStore().dateFormat

function formatDateTime(timestamp: string | number | Date, utc: boolean = true): string {
	return dayjs(timestamp).utc(utc).format(dFormats.datetimesec)
}

const excerpt = computed(() => {
	const text = note.note_details.note_content
	const truncated = text.split(" ").slice(0, 30).join(" ")

	return truncated + (truncated !== text ? "..." : "")
})

const properties = computed(() => {
	return _omit(note.note_details, ["note_content", "custom_attributes", "note_creationdate", "note_lastupdate"])
})
</script>

<style lang="scss" scoped>
.soc-case-note {
	border-radius: var(--border-radius);
	background-color: var(--bg-secondary-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-050);

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

	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
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
