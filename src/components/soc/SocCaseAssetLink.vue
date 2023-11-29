<template>
	<div class="soc-asset-link">
		<div class="flex flex-col gap-2 px-5 py-4">
			<div class="header-box flex justify-between">
				<div class="flex items-center gap-2 cursor-helper">
					<div class="id flex items-center gap-2">
						<span>{{ link.case_name }}</span>
						<Icon :name="InfoIcon" :size="16"></Icon>
					</div>
					<!--
						aggiungere popup con mini view SOC CASE
					-->
				</div>
			</div>
			<div class="main-box flex justify-between gap-4">
				<div class="content">
					<div class="description mt-2" v-if="link.asset_description">{{ link.asset_description }}</div>

					<div class="badges-box flex flex-wrap items-center gap-3 mt-4">
						<Badge type="splitted">
							<template #label>Case open date</template>
							<template #value>{{ formatDate(link.case_open_date) }}</template>
						</Badge>
						<Badge type="splitted">
							<template #label>Asset id</template>
							<template #value>{{ link.asset_id }}</template>
						</Badge>
						<Badge type="splitted">
							<template #label>Compromise status</template>
							<template #value>{{ link.asset_compromise_status_id || "-" }}</template>
						</Badge>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import KVCard from "@/components/common/KVCard.vue"
import Badge from "@/components/common/Badge.vue"
import { computed, ref, watch } from "vue"
import SocCaseTimeline from "./SocCaseTimeline.vue"
import "@/assets/scss/vuesjv-override.scss"
import Api from "@/api"
import { useMessage, NPopover, NSpin, NTimeline, NTimelineItem, NModal, NTabs, NTabPane, NInput } from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import _omit from "lodash/omit"
import _split from "lodash/split"
import _upperFirst from "lodash/upperFirst"
import { useRouter } from "vue-router"
import type { SocAssetLink } from "@/types/soc/asset.d"

const { link } = defineProps<{ link: SocAssetLink }>()

const TimeIcon = "carbon:time"
const InfoIcon = "carbon:information"
const CustomerIcon = "carbon:user"
const LinkIcon = "carbon:launch"
const OwnerIcon = "carbon:user-military"
const StatusIcon = "fluent:status-20-regular"

const showDetails = ref(false)
const loadingDetails = ref(false)
const loadingAssets = ref(false)
const message = useMessage()
const router = useRouter()

const dFormats = useSettingsStore().dateFormat

function formatDate(timestamp: string | number | Date, utc: boolean = true): string {
	return dayjs(timestamp).utc(utc).format(dFormats.date)
}

/*
function getDetails() {
	loadingDetails.value = true

	Api.soc
		.getCases(caseData.case_id.toString())
		.then(res => {
			if (res.data.success) {
				extendedInfo.value = res.data?.case || null
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingDetails.value = false
		})
}

function getAssets() {
	loadingAssets.value = true

	Api.soc
		.getAssetsByCase(caseData.case_id.toString())
		.then(res => {
			if (res.data.success) {
				assetsList.value = res.data?.assets || null
				assetsState.value = res.data?.state || null
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingAssets.value = false
		})
}

watch(showDetails, val => {
	if (val && !extendedInfo.value) {
		getDetails()
	}
	if (val && !assetsList.value) {
		getAssets()
	}
})
*/
</script>

<style lang="scss" scoped>
.soc-asset-link {
	border-radius: var(--border-radius);
	background-color: var(--bg-secondary-color);
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
	}

	.main-box {
		word-break: break-word;

		.description {
			color: var(--fg-secondary-color);
			font-size: 13px;
		}
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}
}
</style>
