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
import { NIcon, NSpace, NSwitch, NCountdown } from "naive-ui"
import ExternalIcon from "@vicons/tabler/ExternalLink"
import { ref } from "vue"

const active = ref(false)
</script>
