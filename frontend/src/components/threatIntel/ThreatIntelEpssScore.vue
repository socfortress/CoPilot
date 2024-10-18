<template>
	<n-spin :show="loading" content-class="min-h-32">
		<div class="mb-4">
			<CardKV>
				<template #key>cve</template>
				<template #value>
					{{ cve }}
				</template>
			</CardKV>
		</div>
		<div v-if="epssList.length" class="flex flex-col gap-3">
			<n-card
				v-for="item of epssList"
				:key="item.___id"
				content-class="bg-secondary"
				class="item-appear item-appear-bottom item-appear-005 overflow-hidden"
			>
				<div class="xs:!flex-row flex flex-col justify-between gap-8">
					<n-statistic class="grow" label="Date">
						<span class="stats-value whitespace-nowrap">
							{{ formatDate(item.date, dFormats.date) }}
						</span>
					</n-statistic>
					<n-statistic class="grow" label="EPSS">
						<span class="stats-value">
							{{ item.epss }}
						</span>
					</n-statistic>
					<n-statistic class="grow" label="Percentile">
						<span class="stats-value">
							{{ item.percentile }}
						</span>
					</n-statistic>
				</div>
			</n-card>
			<p v-if="epssModelLink" class="w-full text-right">
				EPSS Model:
				<a :href="epssModelLink" target="_blank">{{ epssModelLink }}</a>
			</p>
		</div>
		<template v-else>
			<n-empty v-if="!loading" description="No items found" class="h-48 justify-center" />
		</template>
	</n-spin>
</template>

<script setup lang="ts">
import type { EpssScore } from "@/types/threatIntel.d"
import Api from "@/api"
import CardKV from "@/components/common/cards/CardKV.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import { NCard, NEmpty, NSpin, NStatistic, useMessage } from "naive-ui"
import { nanoid } from "nanoid"
import { onBeforeMount, ref } from "vue"

interface EpssScoreExt extends EpssScore {
	___id?: string
}

const { cve } = defineProps<{
	cve: string
}>()

const dFormats = useSettingsStore().dateFormat
const message = useMessage()
const loading = ref(false)
const epssList = ref<EpssScoreExt[]>([])
const epssModelLink = ref<string | null>(null)

function getData() {
	loading.value = true

	Api.threatIntel
		.epssScore(cve)
		.then(res => {
			if (res.data.success) {
				epssList.value = ((res.data.data as EpssScoreExt[]) || []).map(o => {
					o.___id = nanoid()
					return o
				})
				epssModelLink.value = res.data.the_epss_model
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

onBeforeMount(() => {
	getData()
})
</script>

<style lang="scss" scoped>
.stats-value {
	font-family: var(--font-family-mono);
	font-size: clamp(18px, 2.3vw, var(--n-value-font-size));
}
</style>
