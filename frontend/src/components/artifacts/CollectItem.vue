<template>
	<div class="collect-item flex flex-wrap gap-2 p-2" :class="{ embedded }">
		<KVCard v-for="prop of displayData" :key="prop.key" :class="{ 'hide-mobile': prop.hideMobile }">
			<template #key>{{ prop.key }}</template>
			<template #value>{{ prop.value }}</template>
		</KVCard>
		<KVCard class="more" @click="showDetails = true">
			<template #value>
				<div class="h-full w-full flex items-center text-center justify-center">view more...</div>
			</template>
		</KVCard>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', overflow: 'hidden' }"
			:bordered="false"
		>
			<SimpleJsonViewer class="vuesjv-override" :model-value="jsonData" :initialExpandedDepth="2" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import { NModal } from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import type { CollectResult } from "@/types/artifacts.d"
import dayjs from "@/utils/dayjs"
import { SimpleJsonViewer } from "vue-sjv"
import "@/assets/scss/vuesjv-override.scss"
import KVCard from "@/components/common/KVCard.vue"
import { onBeforeMount, ref } from "vue"
import _isString from "lodash/isString"
import _isNumber from "lodash/isNumber"
import { formatDate } from "@/utils"

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
			prop.value = dayjs(value).isValid() ? formatDate(value, dFormats.datetimesec).toString() : value.toString()
		}

		if (prop.value && typeof prop.value === "number") {
			const numText = prop.value.toString()

			if (numText.length === 10 || numText.length === 13) {
				if (dayjs(value).isValid()) {
					prop.value = formatDate(value, dFormats.datetimesec).toString()
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

<style lang="scss" scoped>
.collect-item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	border: var(--border-small-050);
	transition: all 0.2s var(--bezier-ease);
	min-height: 160px;
	max-width: 100%;
	overflow: hidden;

	.kv-card {
		&.more {
			cursor: pointer;
			transition: all 0.2s;

			&:hover {
				border-color: var(--primary-color);
			}
		}
	}

	&:hover {
		border-color: var(--primary-color);
	}

	&.embedded {
		background-color: var(--bg-secondary-color);
	}

	@container (max-width: 500px) {
		flex-direction: column;

		.kv-card {
			flex-basis: initial;
			flex-grow: initial;
		}
		.hide-mobile {
			display: none;
		}
	}
}
</style>
