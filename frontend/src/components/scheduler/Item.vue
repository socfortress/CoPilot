<template>
	<div class="item flex flex-col gap-4 px-5 py-3">
		<div class="header-box flex justify-between gap-4">
			<div class="name">{{ job.id }}</div>
			<div class="time flex items-center gap-2">
				{{ formatDate(job.last_success, dFormats.datetimesec) }}

				<n-tooltip>
					<template #trigger>
						<Icon :name="TimeIcon"></Icon>
					</template>
					Last success time
				</n-tooltip>
			</div>
		</div>
		<div class="main-box flex justify-between gap-4 items-center">
			<div class="content">
				<div class="title">{{ job.name }}</div>
				<div class="description mt-1">{{ job.description }}</div>
				<div class="badges-box flex flex-wrap items-center gap-3 mt-4">
					<Badge type="splitted">
						<template #label>Interval</template>
						<template #value>
							{{ job.time_interval }} {{ job.time_interval === 1 ? "minute" : "minutes" }}
						</template>
					</Badge>
				</div>
			</div>

			<div class="actions-box">
				<JobActions :job="job" />
			</div>
		</div>
		<div class="footer-box flex flex-col gap-4">
			<JobActions :job="job" size="small" inline />
			<div class="time w-full text-right">{{ formatDate(job.last_success, dFormats.datetimesec) }}</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import { NTooltip } from "naive-ui"
import type { Job } from "@/types/scheduler"
import { formatDate } from "@/utils"
import { useSettingsStore } from "@/stores/settings"
import JobActions from "./JobActions.vue"

const { job } = defineProps<{ job: Job }>()

const TimeIcon = "carbon:time"

const dFormats = useSettingsStore().dateFormat
</script>

<style lang="scss" scoped>
.item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-050);

	.header-box {
		font-size: 13px;
		font-family: var(--font-family-mono);
		word-break: break-word;
		color: var(--fg-secondary-color);
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

	.footer-box {
		display: none;
		margin-top: 4px;

		.time {
			font-size: 13px;
			font-family: var(--font-family-mono);
			word-break: break-word;
			color: var(--fg-secondary-color);
		}
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}

	@container (max-width: 450px) {
		.header-box {
			.time {
				display: none;
			}
		}
		.main-box {
			.actions-box {
				display: none;
			}
		}
		.footer-box {
			display: flex;
		}
	}
}
</style>
