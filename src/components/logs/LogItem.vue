<template>
	<div class="log-item flex flex-col gap-2 px-5 py-3" :class="`status-${log.event_type}`">
		<div class="header-box flex justify-between">
			<div class="id">
				<span>{{ log.event_type }} - user: {{ log.user_id }}</span>
			</div>
			<div class="time">
				{{ formatDate(log.timestamp) }}
			</div>
		</div>
		<div class="main-box flex justify-between gap-4">
			<div class="content flex gap-3 items-center">
				<div class="level mt-1">
					<Icon :name="WarningIcon" :size="20" v-if="log.event_type === LogEventType.Error" />
					<Icon :name="OKIcon" :size="20" v-else />
				</div>
				<div class="info grow">
					<div class="message" v-html="log.message"></div>
				</div>
			</div>
		</div>
		<div class="footer-box flex justify-end items-center gap-3">
			<div class="time">{{ formatDate(log.timestamp) }}</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import "@/assets/scss/vuesjv-override.scss"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import { LogEventType, type Log } from "@/types/logs.d"
import { useRouter } from "vue-router"

// TODO: user_id -> http://127.0.0.1:5173/soc/users (gotoUsersPage)
// TODO: use ON LogsList getUsers() to match "user_id"

const { log } = defineProps<{ log: Log }>()

const WarningIcon = "carbon:warning-alt-filled"
const OKIcon = "carbon:checkmark-filled"

const router = useRouter()
const dFormats = useSettingsStore().dateFormat

function formatDate(timestamp: string | number | Date, utc: boolean = true): string {
	return dayjs(timestamp).utc(utc).format(dFormats.datetime)
}

function gotoUsersPage(userId?: string | number) {
	router.push(`/soc/users${userId ? "?user_id=" + userId : ""}`).catch(() => {})
}
</script>

<style lang="scss" scoped>
.log-item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	border: var(--border-small-050);

	.header-box {
		font-family: var(--font-family-mono);
		font-size: 13px;
		.id {
			word-break: break-word;
			color: var(--fg-secondary-color);
			line-height: 1.2;
		}

		.time {
			color: var(--fg-secondary-color);
		}
	}

	.main-box {
		word-break: break-word;

		.level {
			color: var(--success-color);
		}
	}

	.footer-box {
		font-family: var(--font-family-mono);
		font-size: 13px;
		margin-top: 10px;
		display: none;

		.time {
			text-align: right;
			color: var(--fg-secondary-color);
		}
	}

	&.status- {
		&crit {
			border-color: var(--warning-color);

			.level {
				color: var(--warning-color);
			}
		}
	}

	@container (max-width: 450px) {
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
