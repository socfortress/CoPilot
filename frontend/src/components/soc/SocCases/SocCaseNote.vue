<template>
	<div class="soc-case-note">
		<div class="flex flex-col gap-2 px-5 py-4">
			<div class="header-box flex justify-between">
				<div class="flex items-center gap-2">
					<div class="id flex cursor-pointer items-center gap-2" @click="showDetails = true">
						<span>#{{ note.note_id }} - {{ note.note_details.note_uuid }}</span>
						<Icon :name="InfoIcon" :size="16"></Icon>
					</div>
				</div>
				<div class="time">
					<n-popover overlap placement="top-end">
						<template #trigger>
							<div class="flex cursor-help items-center gap-2">
								<span>
									{{ formatDateTime(note.note_details.note_creationdate) }}
								</span>
								<Icon :name="TimeIcon" :size="16"></Icon>
							</div>
						</template>
						<div class="flex flex-col px-1 py-2">
							<SocCaseNoteTimeline :note="note" />
						</div>
					</n-popover>
				</div>
			</div>
			<div class="main-box flex justify-between gap-4">
				<div class="content">
					<div class="title" v-html="note.note_title"></div>
					<div v-if="note.note_details.note_content" class="description mt-2">
						{{ excerpt }}
					</div>

					<!--
						<div class="badges-box flex flex-wrap items-center gap-3 mt-4">
							<Badge type="splitted" color="primary">
								<template #label>Status</template>
								<template #value>{{ asset.analysis_status }}</template>
							</Badge>
							<Badge type="splitted" color="primary">
								<template #label>Type</template>
								<template #value>{{ asset.asset_type }}</template>
							</Badge>
							<Badge type="splitted" color="primary" v-for="tag of tags" :key="tag.key">
								<template #label>{{ tag.key }}</template>
								<template #value v-if="tag.value !== undefined">{{ tag.value || "-" }}</template>
							</Badge>
						</div>
					-->
				</div>
			</div>
			<div class="footer-box flex items-center justify-end gap-3">
				<div class="time">
					{{ formatDateTime(note.note_details.note_creationdate) }}
				</div>
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
					<div v-if="properties" class="grid-auto-fit-200 grid gap-2 p-7 pt-4">
						<CardKV v-for="(value, key) of properties" :key="key">
							<template #key>
								{{ key }}
							</template>
							<template #value>
								{{ value || "-" }}
							</template>
						</CardKV>
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
import type { SocNote } from "@/types/soc/note.d"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import _omit from "lodash/omit"
import { NInput, NModal, NPopover, NTabPane, NTabs } from "naive-ui"
import { computed, defineAsyncComponent, ref } from "vue"

const { note } = defineProps<{ note: SocNote }>()

const SocCaseNoteTimeline = defineAsyncComponent(() => import("./SocCaseNoteTimeline.vue"))

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
