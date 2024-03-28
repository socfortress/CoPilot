<template>
	<div class="item flex flex-col gap-2 px-5 py-3" :class="{ default: stream.is_default }">
		<div class="header-box flex items-center gap-3">
			<div class="info flex items-center gap-2 grow">
				<div class="user flex items-center gap-2">
					<Icon :name="UserIcon" :size="14"></Icon>
					{{ stream.creator_user_id }}
				</div>
			</div>
			<div class="time">{{ formatDate(stream.created_at, dFormats.datetimesec) }}</div>
			<n-button size="small" @click.stop="showDetails = true">
				<template #icon>
					<Icon :name="InfoIcon"></Icon>
				</template>
			</n-button>
		</div>
		<div class="main-box flex justify-between">
			<div class="content">
				<div class="title">{{ stream.title }}</div>
				<div class="description mb-2">{{ stream.description }}</div>
				<div class="badges-box flex flex-wrap items-center gap-3">
					<Badge :type="stream.disabled ? 'muted' : 'active'">
						<template #iconRight>
							<Icon :name="stream.disabled ? DisabledIcon : EnabledIcon" :size="14"></Icon>
						</template>
						<template #label>Enabled</template>
					</Badge>
					<Badge :type="stream.is_default ? 'active' : 'muted'">
						<template #iconRight>
							<Icon :name="stream.is_default ? EnabledIcon : DisabledIcon" :size="14"></Icon>
						</template>
						<template #label>Default</template>
					</Badge>
					<Badge :type="stream.is_editable ? 'active' : 'muted'">
						<template #iconRight>
							<Icon :name="stream.is_editable ? EnabledIcon : DisabledIcon" :size="14"></Icon>
						</template>
						<template #label>Editable</template>
					</Badge>
				</div>
			</div>
			<div class="actions-box flex flex-col justify-end" v-if="stream.is_editable">
				<n-button @click="stop()" :loading="loading" v-if="!stream.disabled">
					<template #icon><Icon :name="StopIcon"></Icon></template>
					Stop stream
				</n-button>
				<n-button @click="start()" :loading="loading" v-else type="primary">
					<template #icon><Icon :name="StartIcon"></Icon></template>
					Start stream
				</n-button>
			</div>
		</div>
		<div class="footer-box flex justify-between items-center">
			<div class="actions-box flex flex-col justify-end" v-if="stream.is_editable">
				<n-button @click="stop()" :loading="loading" v-if="!stream.disabled" size="small">
					<template #icon><Icon :name="StopIcon"></Icon></template>
					Stop
				</n-button>
				<n-button @click="start()" :loading="loading" v-else type="primary" size="small">
					<template #icon><Icon :name="StartIcon"></Icon></template>
					Start
				</n-button>
			</div>
			<div class="time">{{ formatDate(stream.created_at, dFormats.datetimesec) }}</div>
		</div>

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
			<SimpleJsonViewer class="vuesjv-override" :model-value="stream.rules" :initialExpandedDepth="2" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import { type Stream } from "@/types/graylog/stream.d"
import { useSettingsStore } from "@/stores/settings"
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import { formatDate } from "@/utils"
import { NModal, NButton, useMessage } from "naive-ui"
import { ref, toRefs } from "vue"
import { SimpleJsonViewer } from "vue-sjv"
import "@/assets/scss/vuesjv-override.scss"
import Api from "@/api"

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

<style lang="scss" scoped>
.item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-050);

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
