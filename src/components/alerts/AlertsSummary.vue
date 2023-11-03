<template>
	<div class="item flex flex-col mb-2 gap-2 px-5 py-3">
		<div class="header-box flex justify-between">
			<div class="id flex items-center gap-2" @click="gotoIndicesPage(alertsSummary.index_name)">
				<IndexIcon :health="alertsSummary.indexStats?.health" color v-if="alertsSummary.indexStats?.health" />
				<Icon :name="PlaceholderIcon" v-else :size="18" />

				{{ alertsSummary.index_name }}
			</div>
			<div class="total-alerts">
				Alerts:
				<strong>{{ alertsSummary.total_alerts }}</strong>
			</div>
		</div>
		<div class="main-box">
			<div class="alert-list">...</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { type AlertsSummary } from "@/types/alerts.d"
import { NPopover } from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import IndexIcon from "@/components/indices/IndexIcon.vue"
import Icon from "@/components/common/Icon.vue"
import type { IndexStats } from "@/types/indices.d"
import { useRouter } from "vue-router"

export interface AlertsSummaryExt extends AlertsSummary {
	indexStats?: IndexStats
}

const { alertsSummary } = defineProps<{ alertsSummary: AlertsSummaryExt }>()

const InfoIcon = "carbon:information"
const TimeIcon = "carbon:time"
const PlaceholderIcon = "ph:question"

const router = useRouter()
const dFormats = useSettingsStore().dateFormat

function formatDate(timestamp: string): string {
	return dayjs(timestamp).format(dFormats.datetimesec)
}

function gotoIndicesPage(index: string) {
	router.push(`/indices?index_name=${index}`).catch(() => {})
}

/*
export interface AlertSource {
	agent_id: string
	agent_ip: AlertSourceAgentIP
	agent_name: string
	agent_labels_customer: string
	rule_level: number
	rule_description: string
	rule_groups: string
	rule_firedtimes: number
	rule_id: string
	rule_mail: boolean
	source: AlertSourceGl2RemoteIP
	timestamp_utc: string
	syslog_type: AlertSourceSyslogType
	streams: string[]
	decoder_name: AlertSourceDecoderName
	syslog_level: AlertSourceSyslogLevel
	manager_name: string
	location: string
}
*/
</script>

<style lang="scss" scoped>
.item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	transition: all 0.2s var(--bezier-ease);

	.header-box {
		font-family: var(--font-family-mono);
		font-size: 13px;
		.id {
			word-break: break-word;
			color: var(--fg-secondary-color);
			line-height: 1;
			cursor: pointer;

			&:hover {
				color: var(--primary-color);
			}
		}
		.total-alerts {
			color: var(--fg-secondary-color);
		}
	}

	@container (max-width: 650px) {
	}
}
</style>
