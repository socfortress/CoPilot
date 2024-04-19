<template>
	<n-tabs type="line" animated :tabs-padding="24">
		<n-tab-pane name="info" tab="Info" display-directive="show">
			<div class="p-7 pt-4">
				<div class="mb-2">
					Id :
					<code>{{ pipeline?.id }}</code>
				</div>
				<div class="mb-2">
					Created:
					<code>
						{{ pipeline?.created_at ? formatDate(pipeline.created_at, dFormats.datetimesec) : "-" }}
					</code>
				</div>
				<div class="mb-2">
					Modified:
					<code>
						{{ pipeline?.modified_at ? formatDate(pipeline.modified_at, dFormats.datetimesec) : "-" }}
					</code>
				</div>
				<div class="mb-2">
					Errors :
					<code>{{ pipeline?.errors || "-" }}</code>
				</div>
			</div>
		</n-tab-pane>
		<n-tab-pane name="source" tab="Source" display-directive="show">
			<div class="p-7 pt-4">
				<n-input
					:value="pipeline?.source"
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
	</n-tabs>
</template>

<script setup lang="ts">
import { NTabs, NTabPane, NInput } from "naive-ui"
import { toRefs } from "vue"
import type { Pipeline } from "@/types/graylog/pipelines.d"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"

const props = defineProps<{ pipeline?: Pipeline }>()
const { pipeline } = toRefs(props)
const dFormats = useSettingsStore().dateFormat
</script>
