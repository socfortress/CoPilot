<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Menu</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/menu"
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
				<n-space vertical>
					<n-layout has-sider>
						<n-layout-sider
							bordered
							collapse-mode="width"
							:collapsed-width="64"
							:width="240"
							show-trigger
							:inverted="inverted"
						>
							<n-menu
								:dropdown-props="{ scrollable: true }"
								:inverted="inverted"
								:collapsed-width="64"
								:collapsed-icon-size="22"
								:options="menuOptions"
							/>
						</n-layout-sider>
						<n-layout>
							<span>Content</span>
							<n-space>
								<n-switch v-model:value="inverted" />
								inverted
							</n-space>
						</n-layout>
					</n-layout>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space vertical>
						<n-layout has-sider>
							<n-layout-sider
								bordered
								collapse-mode="width"
								:collapsed-width="64"
								:width="240"
								show-trigger
								:inverted="inverted"
							>
								<n-menu
									:dropdown-props="{ scrollable: true }"
									:inverted="inverted"
									:collapsed-width="64"
									:collapsed-icon-size="22"
									:options="menuOptions"
								/>
							</n-layout-sider>
							<n-layout>
								<span>Content</span>
								<n-space>
									<n-switch v-model:value="inverted" />
									inverted
								</n-space>
							</n-layout>
						</n-layout>
					</n-space>
					`) }}

					{{
						js(`
						import { BookOutline as BookIcon, PersonOutline as Perso  WineOutline as WineIcon } from "@vicons/ionicons5"

						function renderIcon(icon: Component) {
							return () => h(  null, { default: () => h(icon) })
						}

						const menuOptions: MenuOption[] = [
							{
								label: "Hear the Wind Sing",
								key: "hear-the-wind-sing",
								icon: renderIcon(BookIcon)
							},
							{
								label: "Pinball 1973",
								key: "pinball-1973",
								icon: renderIcon(BookIcon),
								disabled: true,
								children: [
									{
										label: "Rat",
										key: "rat"
									}
								]
							},
							{
								label: "A Wild Sheep Chase",
								key: "a-wild-sheep-chase",
								disabled: true,
								icon: renderIcon(BookIcon)
							},
							{
								label: "Dance Dance Dance",
								key: "Dance Dance Dance",
								icon: renderIcon(BookIcon),
								children: [
									{
										type: "group",
										label: "People",
										key: "people",
										children: [
											{
												label: "Narrator",
												key: "narrator",
												icon: renderIcon(PersonIcon)
											},
											{
												label: "Sheep Man",
												key: "sheep-man",
												icon: renderIcon(PersonIcon)
											}
										]
									},
									{
										label: "Beverage",
										key: "beverage",
										icon: renderIcon(WineIcon),
										children: [
											{
												label: "Whisky",
												key: "whisky"
											}
										]
									},
									{
										label: "Food",
										key: "food",
										children: [
											{
												label: "Sandwich",
												key: "sandwich"
											}
										]
									},
									{
										label: "The past increases. The future recedes.",
										key: "the-past-increases-the-future-recedes"
									}
								]
							}
						]

						const inverted = ref(false)
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Horizontal">
				<n-menu mode="horizontal" :options="menuOptions" :dropdown-props="{ scrollable: true }" />

				<template #code="{ html, js }">
					{{ html(`
					<n-menu mode="horizontal" :options="menuOptions" :dropdown-props="{ scrollable: true }" />
					`) }}

					{{
						js(`
						import { BookOutline as BookIcon, PersonOutline as Perso  WineOutline as WineIcon } from "@vicons/ionicons5"

						function renderIcon(icon: Component) {
							return () => h(  null, { default: () => h(icon) })
						}

						const menuOptions: MenuOption[] = [
							{
								label: "Hear the Wind Sing",
								key: "hear-the-wind-sing",
								icon: renderIcon(BookIcon)
							},
							{
								label: "Pinball 1973",
								key: "pinball-1973",
								icon: renderIcon(BookIcon),
								disabled: true,
								children: [
									{
										label: "Rat",
										key: "rat"
									}
								]
							},
							{
								label: "A Wild Sheep Chase",
								key: "a-wild-sheep-chase",
								disabled: true,
								icon: renderIcon(BookIcon)
							},
							{
								label: "Dance Dance Dance",
								key: "Dance Dance Dance",
								icon: renderIcon(BookIcon),
								children: [
									{
										type: "group",
										label: "People",
										key: "people",
										children: [
											{
												label: "Narrator",
												key: "narrator",
												icon: renderIcon(PersonIcon)
											},
											{
												label: "Sheep Man",
												key: "sheep-man",
												icon: renderIcon(PersonIcon)
											}
										]
									},
									{
										label: "Beverage",
										key: "beverage",
										icon: renderIcon(WineIcon),
										children: [
											{
												label: "Whisky",
												key: "whisky"
											}
										]
									},
									{
										label: "Food",
										key: "food",
										children: [
											{
												label: "Sandwich",
												key: "sandwich"
											}
										]
									},
									{
										label: "The past increases. The future recedes.",
										key: "the-past-increases-the-future-recedes"
									}
								]
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
import { NSpace, NSwitch, NLayout, NLayoutSider, NMenu, type MenuOption } from "naive-ui"
import { ref } from "vue"
import { renderIcon } from "@/utils"
import Icon from "@/components/common/Icon.vue"

const ExternalIcon = "tabler:external-link"
const BookIcon = "ion:book-outline"
const PersonIcon = "ion:person-outline"
const WineIcon = "ion:wine-outline"

const menuOptions: MenuOption[] = [
	{
		label: "Hear the Wind Sing",
		key: "hear-the-wind-sing",
		icon: renderIcon(BookIcon)
	},
	{
		label: "Pinball 1973",
		key: "pinball-1973",
		icon: renderIcon(BookIcon),
		disabled: true,
		children: [
			{
				label: "Rat",
				key: "rat"
			}
		]
	},
	{
		label: "A Wild Sheep Chase",
		key: "a-wild-sheep-chase",
		disabled: true,
		icon: renderIcon(BookIcon)
	},
	{
		label: "Dance Dance Dance",
		key: "Dance Dance Dance",
		icon: renderIcon(BookIcon),
		children: [
			{
				type: "group",
				label: "People",
				key: "people",
				children: [
					{
						label: "Narrator",
						key: "narrator",
						icon: renderIcon(PersonIcon)
					},
					{
						label: "Sheep Man",
						key: "sheep-man",
						icon: renderIcon(PersonIcon)
					}
				]
			},
			{
				label: "Beverage",
				key: "beverage",
				icon: renderIcon(WineIcon),
				children: [
					{
						label: "Whisky",
						key: "whisky"
					}
				]
			},
			{
				label: "Food",
				key: "food",
				children: [
					{
						label: "Sandwich",
						key: "sandwich"
					}
				]
			},
			{
				label: "The past increases. The future recedes.",
				key: "the-past-increases-the-future-recedes"
			}
		]
	}
]

const inverted = ref(false)
</script>

<style lang="scss" scoped>
.components-list {
	grid-template-columns: none;
}
</style>
