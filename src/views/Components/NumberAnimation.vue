<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Number Animation</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/number-animation"
					target="_blank"
					alt="docs"
					rel="nofollow noopener noreferrer"
					class="ml-4"
				>
					<n-icon :size="16">
						<ExternalIcon />
					</n-icon>
					docs
				</a>
			</div>
		</div>

		<div class="components-list">
			<CardCodeExample title="Basic" class="max-w-lg">
				<n-statistic label="A little goal" tabular-nums>
					<n-number-animation
						ref="numberAnimationInstRef"
						show-separator
						:from="0"
						:to="100000000"
						:active="false"
						:precision="2"
					/>
				</n-statistic>
				<n-button @click="handleClick">Play</n-button>
				<template #code="{ html, js }">
					{{ html(`
					<n-statistic label="A little goal" tabular-nums>
						<n-number-animation
							ref="numberAnimationInstRef"
							show-separator
							:from="0"
							:to="100000000"
							:active="false"
							:precision="2"
						/>
					</n-statistic>
					<n-button @click="handleClick">Play</n-button>
					`) }}

					{{
						js(`
						const numberAnimationInstRef = ref\<\NumberAnimationInst | null\>\(null)

						function handleClick() {
							numberAnimationInstRef.value?.play()
						}
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NIcon, NStatistic, NNumberAnimation, NButton, type NumberAnimationInst } from "naive-ui"
import ExternalIcon from "@vicons/tabler/ExternalLink"
import { ref } from "vue"

const numberAnimationInstRef = ref<NumberAnimationInst | null>(null)

function handleClick() {
	numberAnimationInstRef.value?.play()
}
</script>
