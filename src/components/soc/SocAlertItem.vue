<template>
	<div class="soc-alert-item flex flex-col gap-0">
		<div class="soc-alert-info px-5 py-3 flex flex-col gap-2">
			<div class="header-box flex justify-between">
				<div class="id">
					<n-popover overlap placement="bottom-start">
						<template #trigger>
							<div class="flex items-center gap-2 cursor-help">
								<span>#{{ alert.alert_id }}</span>
								<Icon :name="InfoIcon" :size="16"></Icon>
							</div>
						</template>
						<div class="flex flex-col gap-1">
							<div class="box"></div>
						</div>
					</n-popover>
				</div>
				<div class="time">
					<n-popover overlap placement="bottom-end">
						<template #trigger>
							<div class="flex items-center gap-2 cursor-help">
								<span>
									{{ formatDate(alert.alert_creation_time) }}
								</span>
								<Icon :name="TimeIcon" :size="16"></Icon>
							</div>
						</template>
						<div class="flex flex-col py-2 px-1">
							<n-timeline>
								<n-timeline-item
									v-for="item of history"
									:key="item.label"
									:title="item.label"
									:time="item.timeString"
								/>
							</n-timeline>
						</div>
					</n-popover>
				</div>
			</div>
			<div class="main-box">
				<div class="content">
					<div class="title">{{ alert.alert_title }}</div>
					<div
						class="description mb-2"
						v-if="alert.alert_description && alert.alert_title !== alert.alert_description"
					>
						{{ alert.alert_description }}
					</div>
				</div>
			</div>
			<div class="badges-box flex flex-wrap items-center gap-3 mt-2">
				<n-tooltip placement="top-start" trigger="hover">
					<template #trigger>
						<Badge type="splitted" hint-cursor>
							<template #iconLeft>
								<Icon :name="StatusIcon" :size="14"></Icon>
							</template>
							<template #label>Status</template>
							<template #value>{{ alert.status.status_name }}</template>
						</Badge>
					</template>
					{{ alert.status.status_description }}
				</n-tooltip>
				<Badge type="splitted" :color="alert.severity.severity_id === 5 ? 'danger' : undefined">
					<template #iconLeft>
						<Icon :name="SeverityIcon" :size="13"></Icon>
					</template>
					<template #label>Severity</template>
					<template #value>{{ alert.severity.severity_name }}</template>
				</Badge>
			</div>
		</div>
		<n-collapse>
			<template #arrow>
				<div class="mx-5 flex">
					<Icon :name="ChevronIcon"></Icon>
				</div>
			</template>
			<n-collapse-item>
				<template #header>
					<div class="py-3 -ml-2">Alert details</div>
				</template>
				<AlertItem :alert="alertObject" :hide-actions="true" class="-mt-4" />
			</n-collapse-item>
		</n-collapse>
	</div>
</template>

<script setup lang="ts">
import AlertItem from "@/components/alerts/Alert.vue"
import type { SocAlert } from "@/types/soc/alert.d"
import type { Alert } from "@/types/alerts.d"
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import { onBeforeMount, ref } from "vue"
import { NCollapse, NCollapseItem, NPopover, NTimeline, NTimelineItem, NTooltip } from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import _toNumber from "lodash/toSafeInteger"

const { alert } = defineProps<{ alert: SocAlert }>()

const ChevronIcon = "carbon:chevron-right"
const InfoIcon = "carbon:information"
const TimeIcon = "carbon:time"
const LinkIcon = "carbon:launch"
const StatusIcon = "fluent:status-20-regular"
const SeverityIcon = "bi:shield-exclamation"

const alertObject = ref<Alert>({} as Alert)
const history = ref<
	{
		timeString: string
		label: string
	}[]
>([])

const dFormats = useSettingsStore().dateFormat

function formatDate(timestamp: string | number, utc: boolean = true): string {
	return dayjs(timestamp).utc(utc).format(dFormats.datetimesec)
}

onBeforeMount(() => {
	alertObject.value = {
		_index: "",
		_id: alert.alert_context.alert_id,
		_source: alert.alert_source_content
	} as Alert

	history.value.push({
		timeString: formatDate(alert.alert_source_event_time),
		label: "Source event"
	})

	if (Object.keys(alert.modification_history).length) {
		for (const key in alert.modification_history) {
			const item = alert.modification_history[key]
			history.value.push({
				timeString: formatDate(_toNumber(key) * 1000, false),
				label: item.action + ` [${item.user}]`
			})
		}
	}
})
</script>

<style lang="scss" scoped>
.soc-alert-item {
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

		.actionable {
			cursor: pointer;
			color: var(--primary-color);
		}
	}

	.main-box {
		.content {
			word-break: break-word;

			.description {
				color: var(--fg-secondary-color);
				font-size: 13px;
			}
		}
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}
}
</style>
