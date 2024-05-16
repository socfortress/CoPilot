<template>
	<div class="item flex flex-col mb-2 gap-2 px-5 py-3" :class="{ highlight }" :id="'rule-' + rule.id">
		<div class="header-box flex justify-between">
			<div class="flex items-center gap-3">
				<div class="id">
					<div class="flex items-center gap-2 cursor-pointer" @click="showDetails = true">
						<span>#{{ rule.id }}</span>
						<Icon :name="InfoIcon" :size="16"></Icon>
					</div>
				</div>
			</div>
			<div class="time">
				<n-popover overlap placement="top-end">
					<template #trigger>
						<div class="flex items-center gap-2 cursor-help">
							<span>
								{{ formatDateTime(rule.modified_at) }}
							</span>
							<Icon :name="TimeIcon" :size="16"></Icon>
						</div>
					</template>
					<div class="flex flex-col py-2 px-1">
						<n-timeline>
							<n-timeline-item type="success" title="Created" :time="formatDateTime(rule.created_at)" />
							<n-timeline-item
								v-if="rule.modified_at"
								title="Modified"
								:time="formatDateTime(rule.modified_at)"
							/>
						</n-timeline>
					</div>
				</n-popover>
			</div>
		</div>
		<div class="main-box">
			<div class="title">{{ rule.title }}</div>
			<div class="description">{{ rule.description }}</div>
		</div>
		<div class="footer-box flex justify-end items-center gap-3">
			<div class="time">
				{{ formatDateTime(rule.modified_at) }}
			</div>
		</div>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(600px, 90vw)', overflow: 'hidden' }"
			:title="rule.title"
			:bordered="false"
			segmented
		>
			<div class="p-7 pt-4">
				<div class="mb-2">
					Created:
					<code>{{ formatDateTime(rule.created_at) }}</code>
				</div>
				<div class="mb-2">
					Modified:
					<code>{{ formatDateTime(rule.modified_at) }}</code>
				</div>
				<div class="mb-2">
					Errors :
					<code>{{ rule.errors || "-" }}</code>
				</div>
				<div class="mb-1">Source :</div>
				<n-input
					:value="rule.source"
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
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import { ref, toRefs } from "vue"
import { NModal, NInput, NPopover, NTimeline, NTimelineItem } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import type { PipelineRule } from "@/types/graylog/pipelines.d"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"

const props = defineProps<{ rule: PipelineRule; highlight: boolean | null | undefined }>()
const { rule, highlight } = toRefs(props)

const TimeIcon = "carbon:time"
const InfoIcon = "carbon:information"

const showDetails = ref(false)
const dFormats = useSettingsStore().dateFormat

function formatDateTime(timestamp: string): string {
	return formatDate(timestamp, dFormats.datetimesec).toString()
}
</script>

<style lang="scss" scoped>
.item {
	border-radius: var(--border-radius);
	background-color: var(--bg-secondary-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-100);
	color: var(--fg-color);

	.header-box {
		font-family: var(--font-family-mono);
		font-size: 13px;
		.id {
			word-break: break-word;
			color: var(--fg-secondary-color);

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

	&.highlight {
		background-color: var(--primary-005-color);
		box-shadow: 0px 0px 0px 1px inset var(--primary-030-color);
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
