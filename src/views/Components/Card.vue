<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Card</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/card"
					target="_blank"
					alt="docs"
					rel="nofollow noopener noreferrer"
				>
					<Icon :name="ExternalIcon" :size="16" />
					docs
				</a>
				<router-link :to="{ name: 'Cards-Basic' }">
					<Icon :name="LinkIcon" :size="16" />
					more cards
				</router-link>
			</div>
		</div>

		<div class="components-list">
			<CardCodeExample title="Basic">
				<template #description>A basic card.</template>
				<n-card title="Card">Card Content</n-card>
				<template #code="{ html }">
					{{ html(`
					<n-card title="Card">Card Content</n-card>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Hoverable">
				<n-card title="Card" hoverable>Card Content</n-card>
				<template #code="{ html }">
					{{ html(`
					<n-card title="Card" hoverable>Card Content</n-card>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Slots">
				<template #description>Card has many slots to help you write less code.</template>
				<n-card title="Card Slots Demo">
					<template #header-extra>#header-extra</template>
					Card Content
					<template #footer>#footer</template>
					<template #action>#action</template>
				</n-card>
				<template #code="{ html }">
					{{ html(`
					<n-card title="Card Slots Demo">
						<template #header-extra>#header-extra</template>
						Card Content
						<template #footer>#footer</template>
						<template #action>#action</template>
					</n-card>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Size">
				<template #description>
					Card has
					<n-text code>small</n-text>
					,
					<n-text code>medium</n-text>
					,
					<n-text code>large</n-text>
					,
					<n-text code>huge</n-text>
					sizes.
				</template>
				<n-space vertical>
					<n-card title="Small Card" size="small">Card Content</n-card>
					<n-card title="Medium Card" size="medium">Card Content</n-card>
					<n-card title="Large Card" size="large">Card Content</n-card>
					<n-card title="Huge Card" size="huge">Card Content</n-card>
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-space vertical>
						<n-card title="Small Card" size="small">Card Content</n-card>
						<n-card title="Medium Card" size="medium">Card Content</n-card>
						<n-card title="Large Card" size="large">Card Content</n-card>
						<n-card title="Huge Card" size="huge">Card Content</n-card>
					</n-space>
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NCard, NSpace, NText } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
const LinkIcon = "carbon:link"
import { RouterLink } from "vue-router"
</script>
