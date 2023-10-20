<template>
	<div class="item flex flex-col mb-2 gap-2 px-5 py-3">
		<div class="header-box flex justify-between">
			<div class="caller">{{ message.caller }}</div>
			<div class="time">{{ message.timestamp }}</div>
		</div>
		<div class="main-box">
			<div class="content">{{ message.content }}</div>
		</div>
		<div class="footer-box">
			<div class="time">{{ formatDate(message.timestamp) }}</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { type Message } from "@/types/graylog/index.d"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"

const { message } = defineProps<{ message: Message }>()

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
		.caller {
			word-break: break-word;
			opacity: 0.4;
		}
		.time {
			opacity: 0.5;
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
			opacity: 0.5;
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
			text-align: right;
			display: flex;
		}
	}
}
</style>
