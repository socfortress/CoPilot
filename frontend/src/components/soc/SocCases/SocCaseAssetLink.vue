<template>
	<CardEntity>
		<template #header>{{ link.case_name }}</template>
		<template v-if="link.asset_description" #default>
			<p>
				{{ link.asset_description }}
			</p>
		</template>
		<template #mainExtra>
			<div class="flex flex-wrap items-center gap-3">
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
		</template>

		<template #footer>
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
					<div class="min-h-14">
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
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { SocCaseAssetLink } from "@/types/soc/asset.d"
import type { SocCase } from "@/types/soc/case.d"
import { NCollapse, NCollapseItem, NEmpty, NSpin, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
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
