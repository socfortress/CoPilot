<template>
	<div class="item flex flex-col gap-2 px-5 py-3">
		<div class="header-box flex justify-between">
			<div class="caller">{{ message.caller }}</div>
			<div class="time">{{ formatDate(message.timestamp, dFormats.datetimesec) }}</div>
		</div>
		<div class="main-box">
			<div class="content">{{ message.content }}</div>
		</div>
		<div class="footer-box">
			<div class="time">{{ formatDate(message.timestamp, dFormats.datetimesec) }}</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { type Message } from "@/types/graylog/index.d"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"

const { message } = defineProps<{ message: Message }>()

const dFormats = useSettingsStore().dateFormat
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
