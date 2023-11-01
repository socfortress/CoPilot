<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Breadcrumb</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/breadcrumb"
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
				<n-breadcrumb>
					<n-breadcrumb-item>
						<Icon :name="Cash" />
						Home
					</n-breadcrumb-item>
					<n-breadcrumb-item>
						<Icon :name="Cash" />
						Account
					</n-breadcrumb-item>
					<n-breadcrumb-item>
						<Icon :name="Cash" />
						Category
					</n-breadcrumb-item>
				</n-breadcrumb>
				<template #code="{ html, js }">
					{{ html(`
					<n-breadcrumb>
						<n-breadcrumb-item>
							<n-icon :component="Cash" />
							Home
						</n-breadcrumb-item>
						<n-breadcrumb-item>
							<n-icon :component="Cash" />
							Account
						</n-breadcrumb-item>
						<n-breadcrumb-item>
							<n-icon :component="Cash" />
							Category
						</n-breadcrumb-item>
					</n-breadcrumb>
					`) }}

					{{
						js(`
						import { Cash } from "@vicons/ionicons5"
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Dropdown">
				<template>
					It is possible to pass a custom template when you want to customize the item link to be, for example
					a
					<n-text code>dropdown</n-text>
					or a
					<n-text code>router-link</n-text>
					.
				</template>
				<n-breadcrumb>
					<n-breadcrumb-item>
						<n-dropdown :options="options1">
							<div class="trigger">I'm ok</div>
						</n-dropdown>
					</n-breadcrumb-item>
					<n-breadcrumb-item>
						<n-dropdown :options="options2">
							<div class="trigger">I'm ok</div>
						</n-dropdown>
					</n-breadcrumb-item>
				</n-breadcrumb>
				<template #code="{ html, js }">
					{{ html(`
					<n-breadcrumb>
						<n-breadcrumb-item>
							<n-dropdown :options="options1">
								<div class="trigger">I'm ok</div>
							</n-dropdown>
						</n-breadcrumb-item>
						<n-breadcrumb-item>
							<n-dropdown :options="options2">
								<div class="trigger">I'm ok</div>
							</n-dropdown>
						</n-breadcrumb-item>
					</n-breadcrumb>
					`) }}

					{{
						js(`
						const options1 = [
							{
								label: "David Tao",
								key: 1
							},
							{
								label: "黑色柳丁",
								key: 2
							}
						]
						const options2 = [
							{
								label: "小镇姑娘",
								key: 1
							},
							{
								label: "普通朋友",
								key: 2
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
import { NBreadcrumb, NBreadcrumbItem, NText, NDropdown } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"

const Cash = "ion:cash"

const options1 = [
	{
		label: "David Tao",
		key: 1
	},
	{
		label: "黑色柳丁",
		key: 2
	}
]
const options2 = [
	{
		label: "小镇姑娘",
		key: 1
	},
	{
		label: "普通朋友",
		key: 2
	}
]
</script>
