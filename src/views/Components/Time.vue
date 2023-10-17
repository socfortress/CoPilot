<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Time</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/time"
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
			<CardCodeExample title="Basic" class="max-w-lg">
				<n-time :time="time" />
				<br />
				<br />
				<n-time :time="0" :to="864000000" type="relative" />
				<template #code="{ html }">
					{{ html(`
					<n-time :time="time" />
					<br />
					<br />
					<n-time :time="0" :to="864000000" type="relative" />
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NTime } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"

const time = new Date()
</script>
