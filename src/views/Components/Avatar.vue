<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Avatar</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/avatar"
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
			<CardCodeExample title="Size">
				<template #description>
					Avatar has
					<n-text code>small</n-text>
					,
					<n-text code>medium</n-text>
					and
					<n-text code>large</n-text>
					sizes. You could also use a custom px number for size.
				</template>
				<div class="flex gap-4">
					<n-avatar size="small" src="https://picsum.photos/seed/FsNXmz/460/460" />
					<n-avatar size="medium" src="https://picsum.photos/seed/FsNXmz/460/460" />
					<n-avatar size="large" src="https://picsum.photos/seed/FsNXmz/460/460" />
					<n-avatar :size="48" src="https://picsum.photos/seed/FsNXmz/460/460" />
				</div>
				<template #code="{ html }">
					{{ html(`
					<n-avatar size="small" src="https://picsum.photos/seed/FsNXmz/460/460" />
					<n-avatar size="medium" src="https://picsum.photos/seed/FsNXmz/460/460" />
					<n-avatar size="large" src="https://picsum.photos/seed/FsNXmz/460/460" />
					<n-avatar :size="48" src="https://picsum.photos/seed/FsNXmz/460/460" />
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Shape">
				<template #description>
					Avatar can be
					<n-text code>round</n-text>
				</template>
				<div class="flex gap-4">
					<n-avatar src="https://picsum.photos/seed/FsNXmz/460/460" />
					<n-avatar round src="https://picsum.photos/seed/FsNXmz/460/460" />
				</div>
				<template #code="{ html }">
					{{ html(`
					<n-avatar src="https://picsum.photos/seed/FsNXmz/460/460" />
					<n-avatar round src="https://picsum.photos/seed/FsNXmz/460/460" />
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Badge">
				<template #description>
					Using it with
					<n-text code>badge</n-text>
					would be nice (if you like tons of notifications).
				</template>
				<n-badge value="999+">
					<n-avatar>App</n-avatar>
				</n-badge>
				<template #code="{ html }">
					{{ html(`
					<n-badge value="999+">
						<n-avatar>App</n-avatar>
					</n-badge>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Fallback">
				<template #description>Show 07akioni if loading fails.</template>
				<n-avatar round size="small" src="empty.png" fallback-src="https://picsum.photos/seed/FsNXmz/460/460" />
				<template #code="{ html }">
					{{ html(`
					<n-avatar
						round
						size="small"
						src="empty.png"
						fallback-src="https://picsum.photos/seed/FsNXmz/460/460"
					/>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Content size">
				<template #description>Text is resized to fit the avatar.</template>
				<n-avatar round>ABC</n-avatar>
				<template #code="{ html }">
					{{ html(`
					<n-avatar round>ABC</n-avatar>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Avatar Group">
				<template #description>Crowded people</template>
				<n-avatar-group :options="options" :size="40" :max="3" />
				<template #code="{ html, js }">
					{{ html(`
					<n-avatar-group :options="options" :size="40" :max="3" />
					`) }}
					{{
						js(`
								const options = [
									{
										name: "Leonardo DiCaprio",
										src: "https://picsum.photos/seed/6UEM8dcF/460/460"
									},
									{
										name: "Jennifer Lawrence",
										src: "https://picsum.photos/seed/FsNXmz/460/460"
									},
									{
										name: "Audrey Hepburn",
										src: "https://picsum.photos/seed/6UEM8dcF/460/460"
									},
									{
										name: "Anne Hathaway",
										src: "https://picsum.photos/seed/FsNXmz/460/460"
									},
									{
										name: "Taylor Swift",
										src: "https://picsum.photos/seed/6UEM8dcF/460/460"
									}
								]
							`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NAvatar, NBadge, NAvatarGroup, NText } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"

const options = [
	{
		name: "Leonardo DiCaprio",
		src: "https://picsum.photos/seed/6UEM8dcF/460/460"
	},
	{
		name: "Jennifer Lawrence",
		src: "https://picsum.photos/seed/FsNXmz/460/460"
	},
	{
		name: "Audrey Hepburn",
		src: "https://picsum.photos/seed/6UEM8dcF/460/460"
	},
	{
		name: "Anne Hathaway",
		src: "https://picsum.photos/seed/FsNXmz/460/460"
	},
	{
		name: "Taylor Swift",
		src: "https://picsum.photos/seed/6UEM8dcF/460/460"
	}
]
</script>
