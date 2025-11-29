<template>
	<div>
		<CardEntity :embedded hoverable clickable @click.stop="showDetails = true">
			<template #headerMain>
				<div class="flex items-center gap-2">
					{{ flow.session_id }}
				</div>
			</template>
			<template #headerExtra>
				<n-popover overlap placement="top-end" class="max-h-64" scrollable to="body">
					<template #trigger>
						<div class="flex cursor-help items-center gap-2">
							<span>
								{{ formatDate(flow.start_time, dFormats.datetimesec) }}
							</span>
							<Icon :name="TimeIcon" :size="16" />
						</div>
					</template>
					<div class="flex flex-col px-1 py-2">
						<AgentFlowTimeline :flow="flow" />
					</div>
				</n-popover>
			</template>
			<template #default>
				<div class="flex flex-wrap gap-2">
					<Badge
						v-for="artifact of flow.artifacts_with_results"
						:key="artifact"
						color="primary"
						type="splitted"
					>
						<template #value>
							{{ artifact }}
						</template>
					</Badge>
				</div>
			</template>
			<template #mainExtra>
				<div class="flex flex-wrap items-center gap-3">
					<Badge type="splitted" color="primary">
						<template #label>State</template>
						<template #value>
							{{ flow.state || "-" }}
						</template>
					</Badge>
					<Badge type="splitted" color="primary">
						<template #label>Status</template>
						<template #value>
							{{ flow.status || "-" }}
						</template>
					</Badge>
					<Badge type="splitted" color="primary">
						<template #label>Exec. time</template>
						<template #value>
							{{ executionDuration }}
						</template>
					</Badge>
					<Badge :type="flow.dirty ? 'active' : 'muted'">
						<template #iconRight>
							<Icon :name="flow.dirty ? EnabledIcon : DisabledIcon" :size="14" />
						</template>
						<template #label>Dirty</template>
					</Badge>
					<Badge :type="flow.user_notified ? 'active' : 'muted'">
						<template #iconRight>
							<Icon :name="flow.user_notified ? EnabledIcon : DisabledIcon" :size="14" />
						</template>
						<template #label>User notified</template>
					</Badge>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(550px, 90vh)', overflow: 'hidden' }"
			:title="`Agent Flow: ${flow.session_id}`"
			:bordered="false"
			segmented
		>
			<n-tabs type="line" animated :tabs-padding="24">
				<n-tab-pane name="Info" tab="Info" display-directive="show">
					<div v-if="properties" class="grid-auto-fit-200 grid gap-2 p-7 pt-4">
						<CardKV v-for="(value, key) of properties" :key>
							<template #key>
								{{ key }}
							</template>
							<template #value>
								{{ value === "" ? "-" : (value ?? "-") }}
							</template>
						</CardKV>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Backtrace" tab="Backtrace" display-directive="show">
					<div class="p-7 pt-4">
						<n-input
							:value="flow.backtrace"
							type="textarea"
							readonly
							placeholder="Empty"
							size="large"
							:autosize="{
								minRows: 3,
								maxRows: 18
							}"
						/>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Timeline" tab="Timeline" display-directive="show:lazy">
					<div class="p-7 pt-4">
						<AgentFlowTimeline :flow="flow" />
					</div>
				</n-tab-pane>
				<n-tab-pane name="Logs" tab="Logs" display-directive="show:lazy">
					<div v-if="flow.logs.length" class="p-7 pt-4">
						<ul>
							<li v-for="log of flow.logs" :key="log">
								{{ log }}
							</li>
						</ul>
					</div>
					<n-empty v-else description="No items found" class="h-48 justify-center" />
				</n-tab-pane>
				<n-tab-pane name="Uploaded files" tab="Uploaded files" display-directive="show:lazy">
					<div v-if="flow.uploaded_files.length" class="p-7 pt-4">
						<ul>
							<li v-for="file of flow.uploaded_files" :key="file">
								{{ file }}
							</li>
						</ul>
					</div>
					<n-empty v-else description="No items found" class="h-48 justify-center" />
				</n-tab-pane>
				<n-tab-pane name="Query stats" tab="Query stats" display-directive="show:lazy">
					<div class="p-7 pt-4">
						<template v-if="flow.query_stats.length">
							<AgentFlowQueryStat
								v-for="stat of flow.query_stats"
								:key="stat.first_active + stat.last_active"
								:stat="stat"
								embedded
								class="item-appear item-appear-bottom item-appear-005 mb-2"
							/>
						</template>
						<n-empty v-else description="No items found" class="h-48 justify-center" />
					</div>
				</n-tab-pane>
				<n-tab-pane name="Request" tab="Request" display-directive="show:lazy">
					<div class="p-7 pt-4">
						<SimpleJsonViewer
							class="vuesjv-override"
							:model-value="flow.request"
							:initial-expanded-depth="2"
						/>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Collect" tab="Collect" display-directive="show:lazy">
					<n-scrollbar class="max-h-106" trigger="none">
						<div class="px-7">
							<AgentFlowCollectList :flow="flow" />
						</div>
					</n-scrollbar>
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { FlowResult } from "@/types/flow.d"
import _pick from "lodash/pick"
import { NEmpty, NInput, NModal, NPopover, NScrollbar, NTabPane, NTabs } from "naive-ui"
import { computed, defineAsyncComponent, ref } from "vue"
import { SimpleJsonViewer } from "vue-sjv"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import dayjs from "@/utils/dayjs"
import "@/assets/scss/overrides/vuesjv-override.scss"

const { flow, embedded } = defineProps<{ flow: FlowResult; embedded?: boolean }>()
const AgentFlowTimeline = defineAsyncComponent(() => import("./AgentFlowTimeline.vue"))
const AgentFlowQueryStat = defineAsyncComponent(() => import("./AgentFlowQueryStat.vue"))
const AgentFlowCollectList = defineAsyncComponent(() => import("./AgentFlowCollectList.vue"))

const TimeIcon = "carbon:time"
const DisabledIcon = "carbon:subtract"
const EnabledIcon = "ri:check-line"

const showDetails = ref(false)
const dFormats = useSettingsStore().dateFormat

const executionDuration = computed(() => dayjs.duration(flow.execution_duration).humanize())

const properties = computed(() => {
	return _pick(flow, [
		"client_id",
		"next_response_id",
		"outstanding_requests",
		"total_collected_rows",
		"total_expected_uploaded_bytes",
		"total_loads",
		"total_logs",
		"total_requests",
		"total_uploaded_bytes",
		"total_uploaded_files",
		"user_notified"
	])
})
</script>
