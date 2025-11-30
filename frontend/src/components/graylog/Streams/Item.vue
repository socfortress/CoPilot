<template>
	<div>
		<CardEntity hoverable :highlighted="stream.is_default">
			<template #headerMain>
				<div class="flex items-center gap-2">
					<Icon :name="UserIcon" :size="14" />
					{{ stream.creator_user_id }}
				</div>
			</template>
			<template #headerExtra>{{ formatDate(stream.created_at, dFormats.datetimesec) }}</template>
			<template #default>
				<div class="flex flex-col gap-1">
					{{ stream.title }}

					<p v-if="stream.description && stream.description !== stream.title">
						{{ stream.description }}
					</p>
				</div>
			</template>
			<template #footerMain>
				<div class="flex flex-wrap items-center gap-3">
					<Badge :type="stream.disabled ? 'muted' : 'active'">
						<template #iconRight>
							<Icon :name="stream.disabled ? DisabledIcon : EnabledIcon" :size="14" />
						</template>
						<template #label>Enabled</template>
					</Badge>
					<Badge :type="stream.is_default ? 'active' : 'muted'">
						<template #iconRight>
							<Icon :name="stream.is_default ? EnabledIcon : DisabledIcon" :size="14" />
						</template>
						<template #label>Default</template>
					</Badge>
					<Badge :type="stream.is_editable ? 'active' : 'muted'">
						<template #iconRight>
							<Icon :name="stream.is_editable ? EnabledIcon : DisabledIcon" :size="14" />
						</template>
						<template #label>Editable</template>
					</Badge>
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
					<n-button
						v-if="stream.is_editable && !stream.disabled"
						:loading="loading"
						type="warning"
						secondary
						size="small"
						@click="stop()"
					>
						<template #icon>
							<Icon :name="StopIcon" />
						</template>
						Stop stream
					</n-button>
					<n-button
						v-if="stream.is_editable && stream.disabled"
						:loading="loading"
						type="success"
						secondary
						size="small"
						@click="start()"
					>
						<template #icon>
							<Icon :name="StartIcon" />
						</template>
						Start stream
					</n-button>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(600px, 90vw)', overflow: 'hidden' }"
			:title="stream.title"
			:bordered="false"
			segmented
		>
			<div class="mb-2">
				Matching type :
				<code>{{ stream.matching_type }}</code>
			</div>
			<div class="mb-2">
				Remove matches from default stream :
				<code>{{ stream.remove_matches_from_default_stream }}</code>
			</div>
			<div class="mb-1">Rules :</div>
			<SimpleJsonViewer class="vuesjv-override" :model-value="stream.rules" :initial-expanded-depth="2" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { Stream } from "@/types/graylog/stream.d"
import { NButton, NModal, useMessage } from "naive-ui"
import { ref, toRefs } from "vue"
import { SimpleJsonViewer } from "vue-sjv"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import "@/assets/scss/overrides/vuesjv-override.scss"

const props = defineProps<{ stream: Stream }>()
const { stream } = toRefs(props)

const UserIcon = "carbon:user"
const InfoIcon = "carbon:information"
const DisabledIcon = "carbon:subtract"
const EnabledIcon = "ph:check-bold"
const StopIcon = "carbon:stop"
const StartIcon = "carbon:play"

const message = useMessage()
const loading = ref(false)
const showDetails = ref(false)
const dFormats = useSettingsStore().dateFormat

function stop() {
	loading.value = true

	Api.graylog
		.stopStream(stream.value.id)
		.then(res => {
			if (res.data.success) {
				stream.value.disabled = true
				message.success(res.data?.message || "Stream stopped.")
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
		.startStream(stream.value.id)
		.then(res => {
			if (res.data.success) {
				stream.value.disabled = false
				message.success(res.data?.message || "Stream started.")
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
