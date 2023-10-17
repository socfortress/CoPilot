<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Back Top</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/back-top"
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
				<template #description>
					BackTop will find its first scrollable ascendant element and listen scroll event on it.
				</template>
				<n-back-top :show="true" />
				<template #code="{ html }">
					{{ html(`
					<n-back-top :show="true" />
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NBackTop } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
</script>
