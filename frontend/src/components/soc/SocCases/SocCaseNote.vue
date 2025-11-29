<template>
	<div>
		<CardEntity hoverable clickable @click.stop="showDetails = true">
			<template #headerMain>#{{ note.note_id }} - {{ note.note_details.note_uuid }}</template>
			<template #headerExtra>
				<n-popover overlap placement="top-end">
					<template #trigger>
						<div class="hover:text-primary flex cursor-help items-center gap-2">
							<span>
								{{ formatDateTime(note.note_details.note_creationdate) }}
							</span>
							<Icon :name="TimeIcon" :size="16" />
						</div>
					</template>
					<div class="flex flex-col px-1 py-2">
						<SocCaseNoteTimeline :note="note" />
					</div>
				</n-popover>
			</template>

			<template #default>
				<div class="flex flex-col gap-1">
					<div v-html="note.note_title"></div>
					<p v-if="note.note_details.note_content">
						{{ excerpt }}
					</p>
				</div>
			</template>

			<!--
			<template #mainExtra>
				<div class="flex flex-wrap items-center gap-3">
					<Badge type="splitted" color="primary">
						<template #label>Status</template>
						<template #value>{{ asset.analysis_status }}</template>
					</Badge>
					<Badge type="splitted" color="primary">
						<template #label>Type</template>
						<template #value>{{ asset.asset_type }}</template>
					</Badge>
					<Badge v-for="tag of tags" :key="tag.key" type="splitted" color="primary">
						<template #label>{{ tag.key }}</template>
						<template v-if="tag.value !== undefined" #value>{{ tag.value || "-" }}</template>
					</Badge>
				</div>
			</template>
			-->
		</CardEntity>

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
import _omit from "lodash/omit"
import { NInput, NModal, NPopover, NTabPane, NTabs } from "naive-ui"
import { computed, defineAsyncComponent, ref } from "vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"

const { note } = defineProps<{ note: SocNote }>()

const SocCaseNoteTimeline = defineAsyncComponent(() => import("./SocCaseNoteTimeline.vue"))

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
