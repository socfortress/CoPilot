<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Slider</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/slider"
					target="_blank"
					alt="docs"
					rel="nofollow noopener noreferrer"
				>
					<Icon :name="ExternalIcon" :size="16" />
					docs
				</a>
			</div>
		</div>

		<div class="components-list">
			<CardCodeExample title="Basic">
				<n-slider v-model:value="value" :step="10" />
				<template #code="{ html, js }">
					{{ html(`
					<n-slider v-model:value="value" :step="10" />
					`) }}

					{{ js(`const value = ref(50)`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Range">
				<n-slider v-model:value="value1" range :marks="marks" :step="10" />
				<template #code="{ html, js }">
					{{ html(`
					<n-slider v-model:value="value1" range :marks="marks" :step="10" />
					`) }}
					{{
						js(`
						const value1 = ref([50, 70])
						const marks = {
							34: "Amazing",
							75: "Good"
						}
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Vertical">
				<template #description>
					Set vertical to enable the
					<n-text code>vertical</n-text>
					mode. Its height depends on the height of the container by default, and you can also customize the
					height.
				</template>
				<n-space style="height: 200px; justify-content: center">
					<n-slider :default-value="77" vertical />
					<n-slider :default-value="20" vertical reverse />
					<n-slider :default-value="30" vertical disabled />
					<n-slider v-model:value="value1" :marks="marks1" vertical range />
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space style="height: 200px; justify-content: center">
						<n-slider :default-value="77" vertical />
						<n-slider :default-value="20" vertical reverse />
						<n-slider :default-value="30" vertical disabled />
						<n-slider v-model:value="value1" :marks="marks1" vertical range />
					</n-space>
					`) }}
					{{
						js(`
						const value1 = ref([50, 70])
						const marks1 = {
							20: "Amazing",
							80: "Good"
						}
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NSlider, NText, NSpace } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"

const value = ref(50)

const value1 = ref([50, 70])
const marks = {
	34: "Amazing",
	75: "Good"
}
const marks1 = {
	20: "Amazing",
	80: "Good"
}
</script>
