<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Rate</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/rate"
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
				<n-rate allow-half />
				<template #code="{ html }">
					{{ html(`
					<n-rate allow-half />
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Color">
				<n-rate color="#4fb233" />
				<template #code="{ html }">
					{{ html(`
					<n-rate color="#4fb233" />
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NRate } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
</script>
