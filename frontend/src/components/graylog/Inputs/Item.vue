<template>
	<div class="item flex flex-col gap-2 px-5 py-3">
		<div class="header-box flex items-center gap-3">
			<div class="info flex grow items-center gap-2">
				<div class="user flex items-center gap-2">
					<Icon :name="UserIcon" :size="14"></Icon>
					{{ input.creator_user_id }}
				</div>
			</div>
			<div class="time">
				{{ formatDateTime(input.created_at) }}
			</div>
			<n-button size="small" @click.stop="showDetails = true">
				<template #icon>
					<Icon :name="InfoIcon"></Icon>
				</template>
			</n-button>
		</div>
		<div class="main-box flex justify-between">
			<div class="content">
				<div class="title">
					{{ input.title }}
				</div>
				<div class="name mb-2">
					{{ input.name }}
				</div>
				<div class="badges-box flex flex-wrap items-center gap-3">
					<Badge :type="input.global ? 'active' : 'muted'">
						<template #iconRight>
							<Icon :name="input.global ? GlobalIcon : DisabledIcon" :size="14"></Icon>
						</template>
						<template #label>Global</template>
					</Badge>
					<n-tooltip trigger="hover" :disabled="!isRunning">
						<template #trigger>
							<Badge :type="isRunning ? 'active' : 'muted'" :hint-cursor="isRunning">
								<template #iconRight>
									<Icon :name="isRunning ? TimeIcon : DisabledIcon" :size="14"></Icon>
								</template>
								<template #label>Running</template>
							</Badge>
						</template>
						{{ formatDateTime(input.started_at) }}
					</n-tooltip>
				</div>
			</div>

			<div class="actions-box flex flex-col justify-end">
				<n-button v-if="isRunning" :loading="loading" @click="stop()">
					<template #icon>
						<Icon :name="StopIcon"></Icon>
					</template>
					Stop input
				</n-button>
				<n-button v-else :loading="loading" type="primary" @click="start()">
					<template #icon>
						<Icon :name="StartIcon"></Icon>
					</template>
					Start input
				</n-button>
			</div>
		</div>
		<div class="footer-box flex items-center justify-between">
			<div class="actions-box flex flex-col justify-end">
				<n-button v-if="isRunning" :loading="loading" size="small" @click="stop()">
					<template #icon>
						<Icon :name="StopIcon"></Icon>
					</template>
					Stop
				</n-button>
				<n-button v-else :loading="loading" type="primary" size="small" @click="start()">
					<template #icon>
						<Icon :name="StartIcon"></Icon>
					</template>
					Start
				</n-button>
			</div>

			<div class="time">
				{{ formatDateTime(input.created_at) }}
			</div>
		</div>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(600px, 90vw)', overflow: 'hidden' }"
			:title="input.title"
			:bordered="false"
			segmented
		>
			<n-tabs type="line" animated :tabs-padding="24">
				<n-tab-pane name="info" tab="Info" display-directive="show:lazy">
					<div class="p-7 pt-4">
						<div class="mb-2">
							Id :
							<code>{{ input.id }}</code>
						</div>
						<div class="mb-2">
							Node :
							<code>{{ input.node }}</code>
						</div>
						<div class="mb-2">
							Type :
							<code>{{ input.type }}</code>
						</div>
						<div class="mb-2">
							Content pack :
							<code>{{ input.content_pack || "-" }}</code>
						</div>
						<div class="mb-2">Static fields :</div>
						<SimpleJsonViewer
							class="vuesjv-override"
							:model-value="input.static_fields"
							:initial-expanded-depth="1"
						/>
					</div>
				</n-tab-pane>
				<n-tab-pane name="attributes" tab="Attributes" display-directive="show:lazy">
					<div class="p-7 pt-4">
						<SimpleJsonViewer
							class="vuesjv-override"
							:model-value="input.attributes"
							:initial-expanded-depth="1"
						/>
					</div>
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { InputExtended } from "@/types/graylog/inputs.d"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import { NButton, NModal, NTabPane, NTabs, NTooltip, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import { SimpleJsonViewer } from "vue-sjv"
import "@/assets/scss/vuesjv-override.scss"

const { input } = defineProps<{ input: InputExtended }>()

const emit = defineEmits<{
	(e: "updated"): void
}>()

const UserIcon = "carbon:user"
const InfoIcon = "carbon:information"
const DisabledIcon = "carbon:subtract"
const TimeIcon = "carbon:time"
const GlobalIcon = "ph:globe-light"
const StopIcon = "carbon:stop"
const StartIcon = "carbon:play"

const message = useMessage()
const loading = ref(false)
const showDetails = ref(false)
const isRunning = computed(() => input?.state === "RUNNING")
const dFormats = useSettingsStore().dateFormat

function formatDateTime(timestamp: string): string {
	return formatDate(timestamp, dFormats.datetimesec).toString()
}

function stop() {
	loading.value = true

	Api.graylog
		.stopInput(input.id)
		.then(res => {
			if (res.data.success) {
				emit("updated")
				message.success(res.data?.message || "Successfully stopped input.")
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

function start() {
	loading.value = true

	Api.graylog
		.startInput(input.id)
		.then(res => {
			if (res.data.success) {
				emit("updated")
				message.success(res.data?.message || "Successfully started input.")
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
	background-color: var(--bg-secondary-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-100);

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

		.name {
			color: var(--fg-secondary-color);
			font-size: 13px;
		}
	}

	.footer-box {
		display: none;
		text-align: right;
		font-size: 13px;
		margin-top: 10px;

		.time {
			font-family: var(--font-family-mono);
			color: var(--fg-secondary-color);
			width: 100%;
		}
	}

	&.default {
		background-color: var(--primary-005-color);
		box-shadow: 0px 0px 0px 1px inset var(--primary-030-color);
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
