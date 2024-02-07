<template>
	<div class="log-item flex flex-col gap-2 px-5 py-3" :class="`type-${eventTypeLower}`">
		<div class="header-box flex justify-end">
			<div class="time">
				{{ formatDate(log.timestamp) }}
			</div>
		</div>
		<div class="main-box flex justify-between gap-4">
			<div class="content flex flex-col gap-2">
				<div class="resource flex flex-wrap gap-3">
					<div class="status" :class="`cat-${statusCategory}`">
						<code>{{ log.status_code }}</code>
					</div>
					<div class="method" :class="methodLower">
						<strong>{{ log.method }}</strong>
					</div>
					<div class="route">{{ log.route }}</div>
				</div>
				<div class="title px-1">{{ log.message }}</div>
				<div class="description px-1" v-if="log.additional_info">{{ log.additional_info }}</div>

				<div class="badges-box flex flex-wrap items-center gap-3 mt-2">
					<Badge type="splitted" :color="log.event_type === LogEventType.ERROR ? 'danger' : undefined">
						<template #iconLeft>
							<Icon
								:name="log.event_type === LogEventType.ERROR ? ErrorIcon : InfoIcon"
								:size="14"
							></Icon>
						</template>
						<template #label>Type</template>
						<template #value>{{ log.event_type }}</template>
					</Badge>
					<Badge type="splitted" v-if="log.user_id">
						<template #iconLeft>
							<Icon :name="UserIcon" :size="14"></Icon>
						</template>
						<template #value>
							<span class="flex items-center gap-2">
								<span>#{{ log.user_id }}</span>
								<span v-if="username" class="flex gap-2">
									<span>/</span>
									<span>
										{{ username }}
									</span>
								</span>
							</span>
						</template>
					</Badge>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import { LogEventType, type Log } from "@/types/logs.d"
import Badge from "@/components/common/Badge.vue"
import { computed } from "vue"
import type { AuthUser } from "@/types/auth.d"

const { log, users } = defineProps<{ log: Log; users?: AuthUser[] }>()

const InfoIcon = "carbon:information"
const UserIcon = "carbon:user"
const ErrorIcon = "majesticons:exclamation-line"

const dFormats = useSettingsStore().dateFormat

const statusCategory = computed(() => log.status_code.toString()[0])
const methodLower = computed(() => log.method.toLowerCase())
const eventTypeLower = computed(() => log.event_type.toLowerCase())
const username = computed(() => {
	if (!users?.length) return ""

	const user = users.find(o => o.id.toString() === log.user_id?.toString())

	return user?.username || ""
})

function formatDate(timestamp: string | number | Date, utc: boolean = true): string {
	return dayjs(timestamp).utc(utc).format(dFormats.datetime)
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

		.time {
			color: var(--fg-secondary-color);
		}
	}

	.main-box {
		word-break: break-word;

		.resource {
			background-color: var(--bg-secondary-color);
			font-family: var(--font-family-mono);
			padding: 10px 12px;
			border-radius: var(--border-radius);

			.status {
				&.cat-2 {
					color: var(--success-color);
				}
				&.cat-3 {
					color: var(--success-color);
				}
				&.cat-4 {
					color: var(--warning-color);
				}
				&.cat-5 {
					color: var(--error-color);
				}
			}

			.method {
				color: var(--secondary1-color);
				&.option {
					color: var(--secondary3-color);
				}
				&.put {
					color: var(--secondary2-color);
				}
				&.post {
					color: var(--primary-color);
				}
				&.delete {
					color: var(--secondary4-color);
				}
			}

			.route {
				font-size: 14px;
			}
		}

		.description {
			color: var(--fg-secondary-color);
			font-size: 13px;
		}
	}

	&.type- {
		&error {
			border-color: var(--secondary4-opacity-010-color);

			.resource {
				background-color: var(--secondary4-opacity-005-color);
				border: 1px solid var(--secondary4-opacity-030-color);
			}
		}
	}
}
</style>
