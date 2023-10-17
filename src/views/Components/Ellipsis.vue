<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Ellipsis</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/ellipsis"
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
				<template #description>Basic single line ellipsis with tooltip.</template>
				<n-ellipsis style="max-width: 240px">
					Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium,
					totam rem aperiam
				</n-ellipsis>
				<template #code="{ html }">
					{{ html(`
					<n-ellipsis style="max-width: 240px">
						Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque
						laudantium, totam rem aperiam
					</n-ellipsis>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Line clamp">
				<template #description>
					See
					<a href="https://caniuse.com/?search=line-clamp" target="_blank" rel="nofollow noreferrer noopener">
						caniuse
					</a>
					for compatibility.
				</template>
				<n-ellipsis :line-clamp="2">
					Lorem ipsum dolor sit amet,
					<br />
					consectetur adipiscing elit,
					<br />
					sed do eiusmod tempor incididunt
					<br />
					ut labore et dolore magna aliqua.
					<br />
					Ut enim ad minim veniam,
					<br />
					quis nostrud exercitation ullamco
				</n-ellipsis>
				<template #code="{ html }">
					{{ html(`
					<n-ellipsis :line-clamp="2">
						Lorem ipsum dolor sit amet,
						<br />
						consectetur adipiscing elit,
						<br />
						sed do eiusmod tempor incididunt
						<br />
						ut labore et dolore magna aliqua.
						<br />
						Ut enim ad minim veniam,
						<br />
						quis nostrud exercitation ullamco
					</n-ellipsis>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Expand trigger">
				<template #description>
					Use
					<n-text code>expand-trigger="click"</n-text>
					with the
					<n-text code>line-clamp</n-text>
					parameter to achieve the function of clicking the abbreviated text to expand the complete text.
				</template>
				<n-ellipsis expand-trigger="click" line-clamp="2" :tooltip="false">
					Lorem ipsum dolor sit amet,
					<br />
					consectetur adipiscing elit,
					<br />
					sed do eiusmod tempor incididunt
					<br />
					ut labore et dolore magna aliqua.
					<br />
					Ut enim ad minim veniam,
					<br />
					quis nostrud exercitation ullamco
				</n-ellipsis>
				<template #code="{ html }">
					{{ html(`
					<n-ellipsis expand-trigger="click" line-clamp="2" :tooltip="false">
						Lorem ipsum dolor sit amet,
						<br />
						consectetur adipiscing elit,
						<br />
						sed do eiusmod tempor incididunt
						<br />
						ut labore et dolore magna aliqua.
						<br />
						Ut enim ad minim veniam,
						<br />
						quis nostrud exercitation ullamco
					</n-ellipsis>
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NEllipsis, NText } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
</script>
