<template>
	<div>
		<CardEntity hoverable :embedded>
			<template #headerMain>
				<div class="flex items-center gap-2">
					<Icon :name="UserIcon" :size="14" />
					{{ input.creator_user_id }}
				</div>
			</template>
			<template #headerExtra>{{ formatDateTime(input.created_at) }}</template>
			<template #default>
				<div class="flex flex-col gap-1">
					{{ input.title }}
					<p>
						{{ input.name }}
					</p>
				</div>
			</template>
			<template #footerMain>
				<div class="flex flex-wrap items-center gap-3">
					<Badge :type="input.global ? 'active' : 'muted'">
						<template #iconRight>
							<Icon :name="input.global ? GlobalIcon : DisabledIcon" :size="14" />
						</template>
						<template #label>Global</template>
					</Badge>
					<n-tooltip trigger="hover" :disabled="!isRunning">
						<template #trigger>
							<Badge :type="isRunning ? 'active' : 'muted'" :hint-cursor="isRunning">
								<template #iconRight>
									<Icon :name="isRunning ? TimeIcon : DisabledIcon" :size="14" />
								</template>
								<template #label>Running</template>
							</Badge>
						</template>
						{{ formatDateTime(input.started_at) }}
					</n-tooltip>
				</div>
			</template>
			<template #footerExtra>
				<div class="flex flex-wrap items-center justify-end gap-3">
					<n-button size="small" @click.stop="showDetails = true">
						<template #icon>
							<Icon :name="InfoIcon" />
						</template>
						Details
					</n-button>
					<n-button v-if="isRunning" :loading="loading" type="warning" size="small" secondary @click="stop()">
						<template #icon>
							<Icon :name="StopIcon" />
						</template>
						Stop input
					</n-button>
					<n-button v-else :loading="loading" type="success" secondary size="small" @click="start()">
						<template #icon>
							<Icon :name="StartIcon" />
						</template>
						Start input
					</n-button>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="p-0!"
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
import { NButton, NModal, NTabPane, NTabs, NTooltip, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import { SimpleJsonViewer } from "vue-sjv"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import "@/assets/scss/overrides/vuesjv-override.scss"

const { input, embedded } = defineProps<{ input: InputExtended; embedded?: boolean }>()

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
