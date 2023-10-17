<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Gradient Text</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/gradient-text"
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
			<CardCodeExample title="Type">
				<template #description>A gradient text component can have different types.</template>
				<n-gradient-text type="error">Boom!</n-gradient-text>
				<br />
				<n-gradient-text type="info">Emmm</n-gradient-text>
				<br />
				<n-gradient-text type="warning">Oops!</n-gradient-text>
				<br />
				<n-gradient-text type="success">Haha!</n-gradient-text>
				<template #code="{ html }">
					{{ html(`
					<n-gradient-text type="error">Boom!</n-gradient-text>
					<br />
					<n-gradient-text type="info">Emmm</n-gradient-text>
					<br />
					<n-gradient-text type="warning">Oops!</n-gradient-text>
					<br />
					<n-gradient-text type="success">Haha!</n-gradient-text>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Customizing gradient">
				<template #description>Design it yourself.</template>
				<n-gradient-text :size="20" gradient="linear-gradient(90deg, red 0%, green 50%, blue 100%)">
					A Scribbled Color
				</n-gradient-text>
				<template #code="{ html }">
					{{ html(`
					<n-gradient-text :size="20" gradient="linear-gradient(90deg, red 0%, green 50%, blue 100%)">
						A Scribbled Color
					</n-gradient-text>
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NGradientText } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
</script>
