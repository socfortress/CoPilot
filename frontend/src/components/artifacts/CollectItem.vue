<template>
	<div class="@container">
		<CardEntity :embedded hoverable size="small">
			<div class="grid-auto-fit-200 @lg:grid flex flex-col gap-2">
				<CardKV v-for="prop of displayData" :key="prop.key" :class="{ '@lg:flex hidden': prop.hideMobile }">
					<template #key>
						{{ prop.key }}
					</template>
					<template #value>
						{{ prop.value }}
					</template>
				</CardKV>
				<CardKV class="hover:!border-primary cursor-pointer" @click="showDetails = true">
					<template #value>
						<div class="flex h-full w-full items-center justify-center text-center">view more...</div>
					</template>
				</CardKV>
			</div>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', overflow: 'hidden' }"
			:bordered="false"
			title="Collected Item"
		>
			<SimpleJsonViewer class="vuesjv-override" :model-value="jsonData" :initial-expanded-depth="2" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { CollectResult } from "@/types/artifacts.d"
import _isNumber from "lodash/isNumber"
import _isString from "lodash/isString"
import { NModal } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import { SimpleJsonViewer } from "vue-sjv"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import dayjs from "@/utils/dayjs"
import "@/assets/scss/overrides/vuesjv-override.scss"

interface Prop {
	key: string
	value: string | number
	hideMobile: boolean
}

const { collect, embedded } = defineProps<{ collect: CollectResult; embedded?: boolean }>()

const jsonData = ref<CollectResult>({})
const displayData = ref<Prop[]>([])

const showDetails = ref(false)
const dFormats = useSettingsStore().dateFormat

onBeforeMount(() => {
	for (const key in collect) {
		const value = collect[key]

		const prop: Prop = {
			key: "",
			value: "",
			hideMobile: false
		}

		if ((_isString(value) || _isNumber(value)) && value !== "" && key !== "___id") {
			prop.key = key
			prop.value = value
		}

		if (prop.value && typeof prop.value === "string") {
			prop.value = dayjs(prop.value).isValid()
				? formatDate(prop.value, dFormats.datetimesec).toString()
				: prop.value
		}

		if (prop.value && typeof prop.value === "number") {
			const numText = prop.value.toString()

			if (numText.length === 10 || numText.length === 13) {
				if (dayjs(prop.value).isValid()) {
					prop.value = formatDate(prop.value, dFormats.datetimesec).toString()
				}
			}
		}

		if (prop.key && displayData.value.length < 5) {
			if (displayData.value.length > 2) {
				prop.hideMobile = true
			}
			displayData.value.push(prop)
		}
	}

	jsonData.value = collect

	delete jsonData.value.___id
})
</script>
