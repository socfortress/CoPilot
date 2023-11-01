<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Mention</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/mention"
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
				<n-mention :options="options" :render-label="renderLabel" placeholder="Type '@'" :prefix="['@']" />
				<template #code="{ html, js }">
					{{ html(`
					<n-mention :options="options" :render-label="renderLabel" placeholder="Type '@'" :prefix="['@']" />
					`) }}

					{{
						js(`
						const options = [
							{
								label: "07akioni",
								value: "07akioni"
							},
							{
								label: "star-kirby",
								value: "star-kirby"
							},
							{
								label: "amadeus711",
								value: "amadeus711"
							}
						]
						const renderLabel = (option: MentionOption): VNodeChild =>
							h("div", { style: "display: flex; align-items: center;" }, [
								h(NAvatar, {
									style: "margin-right: 8px;",
									size: 24,
									round: true,
									src: "https://picsum.photos/seed/FsNXmz/460/460"
								}),
								option.value
							])
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Textarea">
				<n-mention type="textarea" :options="options" :autosize="{ minRows: 3 }" />
				<template #code="{ html, js }">
					{{ html(`
					<n-mention type="textarea" :options="options" :autosize="{ minRows: 3 }" />
					`) }}

					{{
						js(`
						const options = [
							{
								label: "07akioni",
								value: "07akioni"
							},
							{
								label: "star-kirby",
								value: "star-kirby"
							},
							{
								label: "amadeus711",
								value: "amadeus711"
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
import { type MentionOption, NAvatar, NMention } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { type VNodeChild, h } from "vue"

const options = [
	{
		label: "07akioni",
		value: "07akioni"
	},
	{
		label: "star-kirby",
		value: "star-kirby"
	},
	{
		label: "amadeus711",
		value: "amadeus711"
	}
]
const renderLabel = (option: MentionOption): VNodeChild =>
	h("div", { style: "display: flex; align-items: center;" }, [
		h(NAvatar, {
			style: "margin-right: 8px;",
			size: 24,
			round: true,
			src: "https://picsum.photos/seed/FsNXmz/460/460"
		}),
		option.value
	])
</script>
