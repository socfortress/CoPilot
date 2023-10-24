<template>
	<div class="item flex flex-col mb-2 gap-2 px-5 py-3">
		<div class="header-box flex justify-between">
			<div class="id">#{{ stream.id }}</div>
			<div class="time">{{ formatDate(stream.created_at) }}</div>
		</div>
		<div class="main-box">
			<div class="title">{{ stream.title }}</div>
			<div class="description">{{ stream.description }}</div>
		</div>
		<div class="footer-box">
			<div class="time">{{ formatDate(stream.created_at) }}</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { type Stream } from "@/types/graylog/stream.d"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"

const { stream } = defineProps<{ stream: Stream }>()

const dFormats = useSettingsStore().dateFormat

function formatDate(timestamp: string): string {
	return dayjs(timestamp).format(dFormats.datetimesec)
}
</script>

<style lang="scss" scoped>
.item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);

	.header-box {
		font-family: var(--font-family-mono);
		font-size: 13px;
		.id {
			word-break: break-word;
			color: var(--fg-secondary-color);
		}
		.time {
			color: var(--fg-secondary-color);
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
		display: none;
		text-align: right;
		font-size: 13px;
		margin-top: 10px;

		.time {
			color: var(--fg-secondary-color);
			width: 100%;
		}
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
