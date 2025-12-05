<template>
	<div :id="`rule-${rule.id}`">
		<CardEntity :highlighted="!!highlight" :embedded hoverable clickable @click.stop="showDetails = true">
			<template #headerMain>#{{ rule.id }}</template>
			<template #headerExtra>
				<n-popover overlap placement="top-end">
					<template #trigger>
						<div class="hover:text-primary flex cursor-help items-center gap-2">
							{{ formatDateTime(rule.modified_at) }}

							<Icon :name="TimeIcon" :size="16" />
						</div>
					</template>
					<div class="flex flex-col px-1 py-2">
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
			</template>
			<template #default>
				<div class="flex flex-col gap-1">
					{{ rule.title }}

					<p v-if="rule.description && rule.description !== rule.title">
						{{ rule.description }}
					</p>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="p-0!"
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
import type { PipelineRule } from "@/types/graylog/pipelines.d"
import { NInput, NModal, NPopover, NTimeline, NTimelineItem } from "naive-ui"
import { ref, toRefs } from "vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"

const props = defineProps<{ rule: PipelineRule; embedded?: boolean; highlight: boolean | null | undefined }>()
const { rule, highlight, embedded } = toRefs(props)

const TimeIcon = "carbon:time"

const showDetails = ref(false)
const dFormats = useSettingsStore().dateFormat

function formatDateTime(timestamp: string): string {
	return formatDate(timestamp, dFormats.datetimesec).toString()
}
</script>
