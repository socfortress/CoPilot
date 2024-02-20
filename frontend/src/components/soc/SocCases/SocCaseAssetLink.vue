<template>
	<div class="soc-asset-link">
		<div class="flex flex-col gap-2 px-5 py-4 pb-2">
			<div class="header-box flex justify-between">
				<div class="flex items-center gap-2 cursor-helper">
					<div class="id flex items-center gap-2">
						<span>{{ link.case_name }}</span>
					</div>
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
		<n-collapse @item-header-click="showSocCase($event.expanded)">
			<template #arrow>
				<div class="mx-5 flex">
					<Icon :name="ChevronIcon"></Icon>
				</div>
			</template>
			<n-collapse-item>
				<template #header>
					<div class="py-3 -ml-2">SOC Case details</div>
				</template>
				<div style="min-height: 50px">
					<n-spin :show="loadingCase">
						<SocCaseItem
							:case-data="socCase"
							v-if="socCase"
							:embedded="true"
							@deleted="getSocCase(link.case_id)"
							class="py-2 -mt-4"
						/>
						<template v-else>
							<n-empty
								description="No Case found"
								class="justify-center h-28 -mt-4"
								v-if="!loadingCase"
							/>
						</template>
					</n-spin>
				</div>
			</n-collapse-item>
		</n-collapse>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import { ref } from "vue"
import Api from "@/api"
import { useMessage, NSpin, NCollapse, NEmpty, NCollapseItem } from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import type { SocCaseAssetLink } from "@/types/soc/asset.d"
import type { SocCase } from "@/types/soc/case.d"
import SocCaseItem from "./SocCaseItem.vue"

const { link } = defineProps<{ link: SocCaseAssetLink }>()

const ChevronIcon = "carbon:chevron-right"

const socCase = ref<SocCase | null>(null)
const loadingCase = ref(false)
const message = useMessage()

const dFormats = useSettingsStore().dateFormat

function formatDate(timestamp: string | number | Date, utc: boolean = true): string {
	return dayjs(timestamp).utc(utc).format(dFormats.date)
}

function showSocCase(show: boolean) {
	if (show && !socCase.value) {
		getSocCase(link.case_id.toString())
	}
}

function getSocCase(caseId: string | number) {
	loadingCase.value = true

	Api.soc
		.getCases(caseId.toString())
		.then(res => {
			if (res.data.success) {
				socCase.value = (res.data?.case as unknown as SocCase) || null
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingCase.value = false
		})
}
</script>

<style lang="scss" scoped>
.soc-asset-link {
	border-radius: var(--border-radius);
	background-color: var(--bg-secondary-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-050);
	container-type: inline-size;

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
			font-size: 13px;
		}
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}
}
</style>
