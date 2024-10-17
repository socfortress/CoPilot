<template>
	<div class="soc-asset-link">
		<div class="flex flex-col gap-2 px-5 py-4 pb-2">
			<div class="header-box flex justify-between">
				<div class="cursor-helper flex items-center gap-2">
					<div class="id flex items-center gap-2">
						<span>{{ link.case_name }}</span>
					</div>
				</div>
			</div>
			<div class="main-box flex justify-between gap-4">
				<div class="content">
					<div v-if="link.asset_description" class="description mt-2">
						{{ link.asset_description }}
					</div>

					<div class="badges-box mt-4 flex flex-wrap items-center gap-3">
						<Badge type="splitted" color="primary">
							<template #label>Case open date</template>
							<template #value>
								{{ formatDate(link.case_open_date) }}
							</template>
						</Badge>
						<Badge type="splitted" color="primary">
							<template #label>Asset id</template>
							<template #value>
								{{ link.asset_id }}
							</template>
						</Badge>
						<Badge type="splitted" color="primary">
							<template #label>Compromise status</template>
							<template #value>
								{{ link.asset_compromise_status_id || "-" }}
							</template>
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
					<div class="-ml-2 py-3">SOC Case details</div>
				</template>
				<div style="min-height: 50px">
					<n-spin :show="loadingCase">
						<SocCaseItem
							v-if="socCase"
							:case-data="socCase"
							:embedded="true"
							class="-mt-4 py-2"
							@deleted="getSocCase(link.case_id)"
						/>
						<template v-else>
							<n-empty
								v-if="!loadingCase"
								description="No Case found"
								class="-mt-4 h-28 justify-center"
							/>
						</template>
					</n-spin>
				</div>
			</n-collapse-item>
		</n-collapse>
	</div>
</template>

<script setup lang="ts">
import type { SocCaseAssetLink } from "@/types/soc/asset.d"
import type { SocCase } from "@/types/soc/case.d"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import { NCollapse, NCollapseItem, NEmpty, NSpin, useMessage } from "naive-ui"
import { ref } from "vue"
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
