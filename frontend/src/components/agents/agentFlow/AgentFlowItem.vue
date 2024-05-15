<template>
	<div class="item flex flex-col gap-2 px-5 py-3" :class="{ embedded }">
		<div class="header-box flex justify-between">
			<div class="flex items-center gap-2">
				<div class="id flex items-center gap-2 cursor-pointer" @click="showDetails = true">
					<span>{{ flow.session_id }}</span>
					<Icon :name="InfoIcon" :size="16"></Icon>
				</div>
			</div>
			<div class="time">
				<n-popover overlap placement="top-end" style="max-height: 240px" scrollable to="body">
					<template #trigger>
						<div class="flex items-center gap-2 cursor-help">
							<span>
								{{ formatDate(flow.start_time, dFormats.datetimesec) }}
							</span>
							<Icon :name="TimeIcon" :size="16"></Icon>
						</div>
					</template>
					<div class="flex flex-col py-2 px-1">
						<AgentFlowTimeline :flow="flow" />
					</div>
				</n-popover>
			</div>
		</div>
		<div class="main-box">
			<div class="content flex flex-wrap gap-2">
				<span v-for="artifact of flow.artifacts_with_results" :key="artifact" class="artifact-label">
					{{ artifact }}
				</span>
			</div>
			<div class="badges-box flex flex-wrap items-center gap-3 mt-4">
				<Badge type="splitted">
					<template #label>State</template>
					<template #value>{{ flow.state || "-" }}</template>
				</Badge>
				<Badge type="splitted">
					<template #label>Status</template>
					<template #value>{{ flow.status || "-" }}</template>
				</Badge>
				<Badge type="splitted">
					<template #label>Exec. time</template>
					<template #value>{{ executionDuration }}</template>
				</Badge>
				<Badge :type="flow.dirty ? 'active' : 'muted'">
					<template #iconRight>
						<Icon :name="flow.dirty ? EnabledIcon : DisabledIcon" :size="14"></Icon>
					</template>
					<template #label>Dirty</template>
				</Badge>
				<Badge :type="flow.user_notified ? 'active' : 'muted'">
					<template #iconRight>
						<Icon :name="flow.user_notified ? EnabledIcon : DisabledIcon" :size="14"></Icon>
					</template>
					<template #label>User notified</template>
				</Badge>
			</div>
		</div>
		<div class="footer-box">
			<div class="time">{{ formatDate(flow.start_time, dFormats.datetimesec) }}</div>
		</div>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(550px, 90vh)', overflow: 'hidden' }"
			:title="'Agent Flow: ' + flow.session_id"
			:bordered="false"
			segmented
		>
			<n-tabs type="line" animated :tabs-padding="24">
				<n-tab-pane name="Info" tab="Info" display-directive="show">
					<div class="grid gap-2 grid-auto-flow-200 p-7 pt-4" v-if="properties">
						<KVCard v-for="(value, key) of properties" :key="key">
							<template #key>{{ key }}</template>
							<template #value>{{ value === "" ? "-" : value ?? "-" }}</template>
						</KVCard>
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
					<div class="p-7 pt-4" v-if="flow.logs.length">
						<ul>
							<li v-for="log of flow.logs" :key="log">{{ log }}</li>
						</ul>
					</div>
					<n-empty v-else description="No items found" class="justify-center h-48" />
				</n-tab-pane>
				<n-tab-pane name="Uploaded files" tab="Uploaded files" display-directive="show:lazy">
					<div class="p-7 pt-4" v-if="flow.uploaded_files.length">
						<ul>
							<li v-for="file of flow.uploaded_files" :key="file">{{ file }}</li>
						</ul>
					</div>
					<n-empty v-else description="No items found" class="justify-center h-48" />
				</n-tab-pane>
				<n-tab-pane name="Query stats" tab="Query stats" display-directive="show:lazy">
					<div class="p-7 pt-4" style="container-type: inline-size">
						<template v-if="flow.query_stats.length">
							<AgentFlowQueryStat
								v-for="stat of flow.query_stats"
								:key="stat.first_active + stat.last_active"
								:stat="stat"
								embedded
								class="mb-2 item-appear item-appear-bottom item-appear-005"
							/>
						</template>
						<n-empty description="No items found" class="justify-center h-48" v-else />
					</div>
				</n-tab-pane>
				<n-tab-pane name="Request" tab="Request" display-directive="show:lazy">
					<div class="p-7 pt-4">
						<SimpleJsonViewer
							class="vuesjv-override"
							:model-value="flow.request"
							:initialExpandedDepth="2"
						/>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Collect" tab="Collect" display-directive="show:lazy">
					<n-scrollbar style="max-height: 430px" trigger="none">
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
import { NPopover, NModal, NTabs, NTabPane, NEmpty, NScrollbar, NInput } from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils"
import type { FlowResult } from "@/types/flow.d"
import Icon from "@/components/common/Icon.vue"
import AgentFlowTimeline from "./AgentFlowTimeline.vue"
import AgentFlowQueryStat from "./AgentFlowQueryStat.vue"
import AgentFlowCollectList from "./AgentFlowCollectList.vue"
import KVCard from "@/components/common/KVCard.vue"
import { computed, ref } from "vue"
import _pick from "lodash/pick"
import Badge from "@/components/common/Badge.vue"
import { SimpleJsonViewer } from "vue-sjv"
import "@/assets/scss/vuesjv-override.scss"

const { flow, embedded } = defineProps<{ flow: FlowResult; embedded?: boolean }>()

const TimeIcon = "carbon:time"
const InfoIcon = "carbon:information"
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

<style lang="scss" scoped>
.item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
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
		.content {
			word-break: break-word;

			.artifact-label {
				background-color: var(--bg-secondary-color);
				padding: 3px 8px;
				border-radius: var(--border-radius);
			}
		}
	}
	.footer-box {
		font-family: var(--font-family-mono);
		display: none;
		text-align: right;
		font-size: 13px;
		margin-top: 10px;

		.time {
			color: var(--fg-secondary-color);
			width: 100%;
		}
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}

	&.embedded {
		background-color: var(--bg-secondary-color);

		.main-box {
			.content {
				.artifact-label {
					background-color: var(--bg-color);
				}
			}
		}
	}

	@container (max-width: 550px) {
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
