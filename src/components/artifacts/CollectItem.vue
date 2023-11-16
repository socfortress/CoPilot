<template>
	<div class="collect-item flex flex-wrap gap-2 p-2">
		<div class="property" v-for="prop of displayData" :key="prop.key" :class="{ 'hide-mobile': prop.hideMobile }">
			<div class="key">{{ prop.key }}</div>
			<div class="value">{{ prop.value }}</div>
		</div>
		<div class="property more" @click="showDetails = true">
			<div class="key">
				<Icon :name="MoreIcon" />
			</div>
		</div>

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
import { onBeforeMount, ref } from "vue"
import _isString from "lodash/isString"
import _isNumber from "lodash/isNumber"
import Icon from "@/components/common/Icon.vue"

const MoreIcon = "mdi:code-json"

interface Prop {
	key: string
	value: string | number
	hideMobile: boolean
}

const { collect } = defineProps<{ collect: CollectResult }>()

const jsonData = ref<CollectResult>({})
const displayData = ref<Prop[]>([])

const showDetails = ref(false)
const dFormats = useSettingsStore().dateFormat

function formatDate(timestamp: string | number): string {
	return dayjs(timestamp).format(dFormats.datetimesec)
}

onBeforeMount(() => {
	for (const key in collect) {
		const value = collect[key]
		console.log(key, value, typeof value)

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
			prop.value = dayjs(value).isValid() ? formatDate(value) : value.toString()
		}

		if (prop.value && typeof prop.value === "number") {
			const numText = prop.value.toString()

			if (numText.length === 10 || numText.length === 13) {
				if (dayjs(value).isValid()) {
					prop.value = formatDate(value)
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

	.property {
		border: var(--border-small-100);
		background-color: var(--bg-secondary-color);
		border-radius: var(--border-radius);
		overflow: hidden;
		flex-basis: 140px;
		flex-grow: 1;

		.key {
			border-bottom: var(--border-small-050);
			padding: 8px 12px;
			font-size: 12px;
		}
		.value {
			font-size: 14px;
			padding: 8px 12px;
			background-color: var(--bg-color);
			font-family: var(--font-family-mono);
			height: 100%;
		}

		&.more {
			cursor: pointer;
			transition: all 0.2s;
			.key {
				border-bottom: none;
				font-size: 26px;
				text-align: center;
				height: 100%;
				display: flex;
				justify-content: center;
				align-items: center;
			}

			&:hover {
				border-color: var(--primary-color);
			}
		}
	}

	&:hover {
		border-color: var(--primary-color);
	}

	@container (max-width: 500px) {
		flex-direction: column;

		.property {
			flex-basis: initial;
			flex-grow: initial;
		}
		.hide-mobile {
			display: none;
		}
	}
}
</style>
