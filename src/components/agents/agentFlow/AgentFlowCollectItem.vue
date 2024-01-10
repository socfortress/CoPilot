<template>
	<div class="item flex flex-col gap-2 px-5 py-3" :class="{ embedded }">
		<div class="header-box flex justify-between">
			<div class="flex items-center gap-2">
				<div class="id">
					<span>{{ collect.Name }}</span>
				</div>
			</div>
			<div class="time">
				{{ formatDate(collect.Timestamp) }}
			</div>
		</div>
		<div class="main-box">
			<div class="content flex flex-wrap gap-4">
				<div class="address-box flex items-center gap-1">
					<div class="flex items-center"><strong>L</strong></div>
					<div>
						ADDR /
						<strong>{{ collect["Laddr.IP"] }}</strong>
					</div>
					<div>
						PORT /
						<strong>{{ collect["Laddr.Port"] }}</strong>
					</div>
				</div>
				<div class="address-box flex items-center gap-1">
					<div class="flex items-center"><strong>R</strong></div>
					<div>
						ADDR /
						<strong>{{ collect["Raddr.IP"] }}</strong>
					</div>
					<div>
						PORT /
						<strong>{{ collect["Raddr.Port"] }}</strong>
					</div>
				</div>
			</div>
			<div class="badges-box flex flex-wrap items-center gap-3 mt-4">
				<Badge type="splitted">
					<template #label>Pid</template>
					<template #value>{{ collect.Pid || "-" }}</template>
				</Badge>
				<Badge type="splitted">
					<template #label>Family</template>
					<template #value>{{ collect.Family || "-" }}</template>
				</Badge>
				<Badge type="splitted">
					<template #label>Status</template>
					<template #value>{{ collect.Status || "-" }}</template>
				</Badge>
				<Badge type="splitted">
					<template #label>Type</template>
					<template #value>{{ collect.Type || "-" }}</template>
				</Badge>
			</div>
		</div>
		<div class="footer-box">
			<div class="time">{{ formatDate(collect.Timestamp) }}</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import type { CollectResult } from "@/types/flow.d"
import Badge from "@/components/common/Badge.vue"

const { collect, embedded } = defineProps<{ collect: CollectResult; embedded?: boolean }>()

const dFormats = useSettingsStore().dateFormat

function formatDate(timestamp: string): string {
	return dayjs(timestamp).format(dFormats.datetimesec)
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

			.address-box {
				font-size: 14px;
				align-items: stretch;

				strong {
					font-family: var(--font-family-mono);
				}

				& > div {
					background-color: var(--secondary1-opacity-010-color);
					padding: 3px 8px;
					border-radius: var(--border-radius-small);
				}

				&:last-child {
					& > div {
						background-color: var(--secondary2-opacity-010-color);
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
