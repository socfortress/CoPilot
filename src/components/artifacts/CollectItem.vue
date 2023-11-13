<template>
	<div class="collect-item flex flex-col gap-2 px-5 py-3">
		<div class="header-box flex justify-between">
			<div class="name">#{{ collect.Pid }}</div>
			<div class="time">{{ formatDate(collect.Timestamp) }}</div>
		</div>
		<div class="main-box">
			<div class="content">
				<div class="name mb-2">{{ collect.Name }}</div>
				<div class="address flex items-center gap-2">
					<Icon :name="NetworkIcon"></Icon>
					<span>Laddr - {{ collect["Laddr.IP"] }}:{{ collect["Laddr.Port"] }}</span>
				</div>
				<div class="address flex items-center gap-2">
					<Icon :name="NetworkIcon"></Icon>
					<span>Raddr - {{ collect["Raddr.IP"] }}:{{ collect["Raddr.Port"] }}</span>
				</div>

				<div class="badges-box flex flex-wrap items-center gap-3">
					<div class="badge splitted">
						<span>family</span>
						<span>{{ collect.Family || "-" }}</span>
					</div>

					<div class="badge splitted">
						<span>type</span>
						<span>{{ collect.Type || "-" }}</span>
					</div>
					<div class="badge splitted">
						<span>status</span>
						<span>{{ collect.Status || "-" }}</span>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/stores/settings"
import type { CollectResult } from "@/types/artifacts.d"
import Icon from "@/components/common/Icon.vue"
import dayjs from "@/utils/dayjs"

const { collect } = defineProps<{ collect: CollectResult }>()

const NetworkIcon = "mdi:server-network-outline"

const dFormats = useSettingsStore().dateFormat

function formatDate(timestamp: string): string {
	return dayjs(timestamp).format(dFormats.datetimesec)
}
</script>

<style lang="scss" scoped>
.collect-item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	transition: all 0.2s var(--bezier-ease);
	max-width: 100%;

	.header-box {
		font-family: var(--font-family-mono);
		font-size: 14px;
		.name {
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
			.address {
				font-family: var(--font-family-mono);
				color: var(--fg-secondary-color);
			}

			.badges-box {
				margin-top: 16px;

				.badge {
					border-radius: var(--border-radius);
					border: var(--border-small-100);
					display: flex;
					align-items: center;
					font-size: 14px;
					padding: 0px 6px;
					height: 26px;
					line-height: 1;
					gap: 6px;
					transition: all 0.3s var(--bezier-ease);

					&.splitted {
						padding: 0px;
						gap: 0;
						overflow: hidden;

						span {
							padding: 0px 8px;
							height: 100%;
							line-height: 24px;
							opacity: 1;

							&:first-child {
								border-right: var(--border-small-100);
								background-color: var(--primary-005-color);
							}
						}
					}
				}
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
}
</style>
