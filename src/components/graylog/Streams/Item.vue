<template>
	<div class="item flex flex-col mb-2 gap-2 px-5 py-3" :class="{ default: stream.is_default }">
		<div class="header-box flex justify-between">
			<div class="info flex items-center gap-2">
				<div class="user flex items-center gap-2">
					<Icon :name="UserIcon" :size="14"></Icon>
					{{ stream.creator_user_id }}
				</div>
			</div>
			<div class="time">{{ formatDate(stream.created_at) }}</div>
		</div>
		<div class="main-box flex justify-between">
			<div class="content">
				<div class="title">{{ stream.title }}</div>
				<div class="description mb-2">{{ stream.description }}</div>
				<div class="badges-box flex flex-wrap items-center gap-3">
					<div class="badge cursor" @click="showDetails = true">
						<Icon :name="InfoIcon" :size="14"></Icon>
					</div>
					<div class="badge" :class="{ active: !stream.disabled }">
						<span>Enabled</span>
						<Icon :name="stream.disabled ? DisabledIcon : EnabledIcon" :size="14"></Icon>
					</div>
					<div class="badge" :class="{ active: stream.is_default }">
						<span>Default</span>
						<Icon :name="stream.is_default ? EnabledIcon : DisabledIcon" :size="14"></Icon>
					</div>
					<div class="badge" :class="{ active: stream.is_editable }">
						<span>Editable</span>
						<Icon :name="stream.is_editable ? EnabledIcon : DisabledIcon" :size="14"></Icon>
					</div>
				</div>
			</div>
			<div class="actions-box flex flex-col justify-end">
				<n-button @click="stop()" :loading="loading">
					<template #icon>
						<Icon :name="StopIcon"></Icon>
					</template>
					Stop stream
				</n-button>
			</div>
		</div>
		<div class="footer-box">
			<div class="time">{{ formatDate(stream.created_at) }}</div>
		</div>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(600px, 90vw)', overflow: 'hidden' }"
			:title="stream.title"
			:bordered="false"
			segmented
		>
			<p class="mb-2">
				Matching type :
				<code>{{ stream.matching_type }}</code>
			</p>
			<p class="mb-2">
				Remove matches from default stream :
				<code>{{ stream.remove_matches_from_default_stream }}</code>
			</p>
			<p class="mb-1">Rules :</p>
			<JsonTreeView :data="rules" :colorScheme="theme" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import { type Stream } from "@/types/graylog/stream.d"
import { useSettingsStore } from "@/stores/settings"
import Icon from "@/components/common/Icon.vue"
import dayjs from "@/utils/dayjs"
import { NModal, NButton, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import { JsonTreeView } from "json-tree-view-vue3"
import Api from "@/api"
import { useThemeStore } from "@/stores/theme"

const { stream } = defineProps<{ stream: Stream }>()

const UserIcon = "carbon:user"
const InfoIcon = "carbon:information"
const DisabledIcon = "ph:minus-bold"
const EnabledIcon = "ph:check-bold"
const StopIcon = "carbon:stop"
const StartIcon = "carbon:play"

const message = useMessage()
const loading = ref(false)
const showDetails = ref(false)
const rules = stream?.rules ? JSON.stringify(stream.rules) : ""
const theme = computed(() => useThemeStore().themeName)
const dFormats = useSettingsStore().dateFormat

function formatDate(timestamp: string): string {
	return dayjs(timestamp).format(dFormats.datetimesec)
}

function stop() {
	loading.value = true

	Api.graylog
		.stopStream(stream.id)
		.then(res => {
			if (res.data.success) {
				console.log(res.data)
				message.success("Stream stopped.")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}
</script>

<style lang="scss" scoped>
.item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);

	.header-box {
		font-family: var(--font-family-mono);
		font-size: 13px;
		.user {
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

		.badges-box {
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

				span,
				i {
					opacity: 0.5;
				}

				&.active {
					color: var(--primary-color);
					background-color: var(--primary-005-color);

					span,
					i {
						opacity: 1;
					}

					border-color: var(--primary-color);
				}

				&.cursor {
					cursor: pointer;

					i {
						opacity: 1;
					}

					&:hover {
						color: var(--primary-color);
						border-color: var(--primary-color);
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

	&.default {
		background-color: var(--primary-005-color);
		box-shadow: 0px 0px 0px 1px inset var(--primary-030-color);
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
