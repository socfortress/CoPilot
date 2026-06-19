<template>
	<div class="@container">
		<CardEntity :embedded hoverable size="small">
			<template v-if="primaryProp" #headerMain>
				<div class="flex min-w-0 flex-col gap-0">
					<p class="text-secondary font-mono text-xs">{{ primaryProp.key }}</p>
					<p class="text-default truncate text-sm font-semibold">{{ primaryProp.value }}</p>
				</div>
			</template>

			<template #headerExtra>
				<n-button size="small" @click.stop="showDetails = true">
					<template #icon>
						<Icon :name="DetailsIcon" />
					</template>
					Details
				</n-button>
			</template>

			<template v-if="badgeProps.length" #default>
				<div class="flex flex-wrap gap-2">
					<Badge
						v-for="prop of badgeProps"
						:key="prop.key"
						type="splitted"
						size="small"
						:class="{ 'hidden @lg:flex': prop.hideMobile }"
					>
						<template #label>{{ prop.key }}</template>
						<template #value>
							<span class="font-mono">{{ prop.value }}</span>
						</template>
					</Badge>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="p-0!"
			:style="{ maxWidth: 'min(800px, 90vw)', overflow: 'hidden' }"
			:bordered="false"
			title="Collected Item"
			segmented
		>
			<SimpleJsonViewer class="vuesjv-override" :model-value="jsonData" :initial-expanded-depth="2" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { CollectResult } from "@/types/artifacts.d"
import _isNumber from "lodash/isNumber"
import _isString from "lodash/isString"
import { NButton, NModal } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import { SimpleJsonViewer } from "vue-sjv"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils/format"
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

const DetailsIcon = "carbon:information"

const primaryProp = computed(() => displayData.value[0] ?? null)
const badgeProps = computed(() => displayData.value.slice(1))

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
