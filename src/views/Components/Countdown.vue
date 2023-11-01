<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Countdown</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/countdown"
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
				<template #description>A countdown string.</template>
				<n-space>
					<n-switch v-model:value="active" />
					<span style="font-variant-numeric: tabular-nums">
						<n-countdown :duration="5000" :active="active" />
					</span>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space>
						<n-switch v-model:value="active" />
						<span style="font-variant-numeric: tabular-nums">
							<n-countdown :duration="5000" :active="active" />
						</span>
					</n-space>
					`) }}

					{{
						js(`
						const active = ref(false)
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NSpace, NSwitch, NCountdown } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"

const active = ref(false)
</script>
