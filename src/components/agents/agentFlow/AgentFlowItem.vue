<template>
	<div class="item flex flex-col gap-2 px-5 py-3">
		<div class="header-box flex justify-between">
			<div class="caller">{{ flow.backtrace }}</div>
			<div class="time">
				<n-popover overlap placement="top-end" style="max-height: 240px" scrollable to="body">
					<template #trigger>
						<div class="flex items-center gap-2 cursor-help">
							<span>
								{{ formatDate(flow.start_time) }}
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
			<div class="content">{{ flow.client_id }}</div>
		</div>
		<div class="footer-box">
			<div class="time">{{ formatDate(flow.start_time) }}</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { NPopover } from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import type { FlowResult } from "@/types/flow.d"
import Icon from "@/components/common/Icon.vue"
import AgentFlowTimeline from "./AgentFlowTimeline.vue"

const { flow } = defineProps<{ flow: FlowResult }>()

const TimeIcon = "carbon:time"

const dFormats = useSettingsStore().dateFormat

function formatDate(timestamp: number): string {
	return dayjs(timestamp / 1000).format(dFormats.datetimesec)
}
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
		.caller {
			word-break: break-word;
			color: var(--fg-secondary-color);
		}
		.time {
			color: var(--fg-secondary-color);
		}
	}
	.main-box {
		.content {
			word-break: break-word;
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
