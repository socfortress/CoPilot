<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Dropdown</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/dropdown"
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
				<template #description>A basic dropdown.</template>
				<n-dropdown trigger="hover" :options="options" @select="handleSelect" :scrollable="true">
					<n-button>Go For a Trip</n-button>
				</n-dropdown>
				<template #code="{ html, js }">
					{{ html(`
					<n-dropdown trigger="hover" :options="options" @select="handleSelect" :scrollable="true">
						<n-button>Go For a Trip</n-button>
					</n-dropdown>
					`) }}
					{{
						js(`
						import { PersonCircleOutline as UserIcon, Pencil as EditIcon, LogOutOutline as LogoutIcon } from "@vicons/ionicons5"

						const renderIcon = (icon: Component) => {
							return () => {
								return h(  null, {
									default: () => h(icon)
								})
							}
						}

						const message = useMessage()
						const options = ref([
							{
								label: "Marina Bay Sands",
								key: "marina bay sands",
								disabled: true,
								icon: renderIcon(UserIcon)
							},
							{
								label: "Brown's Hotel, London",
								key: "brown's hotel, london",
								icon: renderIcon(EditIcon)
							},
							{
								label: "Atlantis Bahamas, Nassau",
								key: "atlantis nahamas, nassau",
								icon: renderIcon(LogoutIcon)
							},
							{
								label: "The Beverly Hills Hotel, Los Angeles",
								key: "the beverly hills hotel, los angeles",
								icon: renderIcon(ExternalIcon)
							}
						])
						function handleSelect(key: string | number) {
							message.info(String(key))
						}
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Trigger">
				<template #description>
					Different ways to
					<n-text code>trigger</n-text>
					/
					<n-text code>show</n-text>
					a dropdown.
				</template>
				<n-space>
					<n-dropdown trigger="hover" :options="options" @select="handleSelect" :scrollable="true">
						<n-button>Hover!</n-button>
					</n-dropdown>
					<n-dropdown trigger="click" :options="options" @select="handleSelect" :scrollable="true">
						<n-button>Click!</n-button>
					</n-dropdown>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space>
						<n-dropdown trigger="hover" :options="options" @select="handleSelect" :scrollable="true">
							<n-button>Hover!</n-button>
						</n-dropdown>
						<n-dropdown trigger="click" :options="options" @select="handleSelect" :scrollable="true">
							<n-button>Click!</n-button>
						</n-dropdown>
					</n-space>
					`) }}

					{{
						js(`
						import { PersonCircleOutline as UserIcon, Pencil as EditIcon, LogOutOutline as LogoutIcon } from "@vicons/ionicons5"

						const renderIcon = (icon: Component) => {
							return () => {
								return h(  null, {
									default: () => h(icon)
								})
							}
						}

						const showDropdown = ref(false)
						const message = useMessage()
						const options = ref([
							{
								label: "Marina Bay Sands",
								key: "marina bay sands",
								disabled: true,
								icon: renderIcon(UserIcon)
							},
							{
								label: "Brown's Hotel, London",
								key: "brown's hotel, london",
								icon: renderIcon(EditIcon)
							},
							{
								label: "Atlantis Bahamas, Nassau",
								key: "atlantis nahamas, nassau",
								icon: renderIcon(LogoutIcon)
							},
							{
								label: "The Beverly Hills Hotel, Los Angeles",
								key: "the beverly hills hotel, los angeles",
								icon: renderIcon(ExternalIcon)
							}
						])
						function handleSelect(key: string | number) {
							message.info(String(key))
						}
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Cascade">
				<template #description>Dropdown options can be cascaded.</template>
				<n-dropdown
					:options="options"
					placement="bottom-start"
					trigger="click"
					@select="handleSelect"
					:scrollable="true"
				>
					<n-button>The Great Gatsby characters</n-button>
				</n-dropdown>
				<template #code="{ html, js }">
					{{ html(`
					<n-dropdown
						:options="options"
						placement="bottom-start"
						trigger="click"
						@select="handleSelect"
						:scrollable="true"
					>
						<n-button>The Great Gatsby characters</n-button>
					</n-dropdown>
					`) }}
					{{
						js(`
						import {
							PersonCircleOutline as UserIcon,
							Pencil as EditIcon,
							LogOutOutline as LogoutIcon,
							ArrowRedoOutline
						} from "@vicons/ionicons5"

						const renderIcon = (icon: Component) => {
							return () => {
								return h(  null, {
									default: () => h(icon)
								})
							}
						}

						const showDropdown = ref(false)
						const message = useMessage()
						const options = ref([
							{
								label: "Marina Bay Sands",
								key: "marina bay sands",
								disabled: true,
								icon: renderIcon(UserIcon)
							},
							{
								label: "Brown's Hotel, London",
								key: "brown's hotel, london",
								icon: renderIcon(EditIcon)
							},
							{
								label: "Cascade",
								key: "cascade",
								icon: renderIcon(ArrowRedoOutline),
								children: [
									{
										label: "Jordan Baker",
										key: "jordan baker"
									},
									{
										label: "Tom Buchanan",
										key: "tom buchanan"
									},
									{
										label: "Others",
										key: "others2",
										disabled: true,
										children: [
											{
												label: "Chicken",
												key: "chicken"
											},
											{
												label: "Beef",
												key: "beef"
											}
										]
									}
								]
							},
							{
								label: "Atlantis Bahamas, Nassau",
								key: "atlantis nahamas, nassau",
								icon: renderIcon(LogoutIcon)
							},
							{
								label: "The Beverly Hills Hotel, Los Angeles",
								key: "the beverly hills hotel, los angeles",
								icon: renderIcon(ExternalIcon)
							}
						])
						function handleSelect(key: string | number) {
							message.info(String(key))
						}
						function handleClick() {
							showDropdown.value = !showDropdown.value
						}
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Manually positioned">
				<template #description>
					Warning: when manually positioned, the
					<n-text code>trigger</n-text>
					prop must be set to
					<n-text code>'manual'</n-text>
					.
				</template>
				<div
					style="width: 200px; height: 200px; background-color: rgba(0, 128, 0, 0.5)"
					@contextmenu="handleContextMenu"
				>
					Right Click
				</div>
				<n-dropdown
					placement="bottom-start"
					trigger="manual"
					:scrollable="true"
					:x="xRef"
					:y="yRef"
					:options="options"
					:show="showDropdown"
					:on-clickoutside="onClickoutside"
					@select="handleSelect"
				/>
				<template #code="{ html, js }">
					{{ html(`
					<div
						style="width: 200px; height: 200px; background-color: rgba(0, 128, 0, 0.5)"
						@contextmenu="handleContextMenu"
					>
						Right Click
					</div>
					<n-dropdown
						placement="bottom-start"
						trigger="manual"
						:scrollable="true"
						:x="xRef"
						:y="yRef"
						:options="options"
						:show="showDropdown"
						:on-clickoutside="onClickoutside"
						@select="handleSelect"
					/>
					`) }}
					{{
						js(`						
						import {
							PersonCircleOutline as UserIcon,
							Pencil as EditIcon,
							LogOutOutline as LogoutIcon,
							ArrowRedoOutline
						} from "@vicons/ionicons5"

						const renderIcon = (icon: Component) => {
							return () => {
								return h(  null, {
									default: () => h(icon)
								})
							}
						}

						const xRef = ref(0)
						const yRef = ref(0)
						const showDropdown = ref(false)
						const message = useMessage()
						const options = ref([
							{
								label: "Marina Bay Sands",
								key: "marina bay sands",
								disabled: true,
								icon: renderIcon(UserIcon)
							},
							{
								label: "Brown's Hotel, London",
								key: "brown's hotel, london",
								icon: renderIcon(EditIcon)
							},
							{
								label: "Cascade",
								key: "cascade",
								icon: renderIcon(ArrowRedoOutline),
								children: [
									{
										label: "Jordan Baker",
										key: "jordan baker"
									},
									{
										label: "Tom Buchanan",
										key: "tom buchanan",
										disabled: true
									},
									{
										label: "Others",
										key: "others2",
										children: [
											{
												label: "Chicken",
												key: "chicken"
											},
											{
												label: "Beef",
												key: "beef"
											}
										]
									}
								]
							},
							{
								label: "Atlantis Bahamas, Nassau",
								key: "atlantis nahamas, nassau",
								icon: renderIcon(LogoutIcon)
							},
							{
								label: "The Beverly Hills Hotel, Los Angeles",
								key: "the beverly hills hotel, los angeles",
								icon: renderIcon(ExternalIcon)
							}
						])
						function handleSelect(key: string | number) {
							message.info(String(key))
						}
						function handleContextMenu(e: MouseEvent) {
							e.preventDefault()
							showDropdown.value = false
							nextTick().then(() => {
								showDropdown.value = true
								xRef.value = e.clientX
								yRef.value = e.clientY
							})
						}
						function onClickoutside() {
							message.info("clickoutside")
							showDropdown.value = false
						}
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NDropdown, NButton, useMessage, NSpace, NText } from "naive-ui"
import { nextTick, ref } from "vue"
import { renderIcon } from "@/utils"

import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"

const UserIcon = "ion:person-circle-outline"
const EditIcon = "ion:pencil"
const LogoutIcon = "ion:log-out-outline"
const ArrowRedoOutline = "ion:arrow-redo-outline"

const xRef = ref(0)
const yRef = ref(0)
const showDropdown = ref(false)
const message = useMessage()
const options = ref([
	{
		label: "Marina Bay Sands",
		key: "marina bay sands",
		disabled: true,
		icon: renderIcon(UserIcon)
	},
	{
		label: "Brown's Hotel, London",
		key: "brown's hotel, london",
		icon: renderIcon(EditIcon)
	},
	{
		label: "Cascade",
		key: "cascade",
		icon: renderIcon(ArrowRedoOutline),
		children: [
			{
				label: "Jordan Baker",
				key: "jordan baker"
			},
			{
				label: "Tom Buchanan",
				key: "tom buchanan",
				disabled: true
			},
			{
				label: "Others",
				key: "others2",
				children: [
					{
						label: "Chicken",
						key: "chicken"
					},
					{
						label: "Beef",
						key: "beef"
					}
				]
			}
		]
	},
	{
		label: "Atlantis Bahamas, Nassau",
		key: "atlantis nahamas, nassau",
		icon: renderIcon(LogoutIcon)
	},
	{
		label: "The Beverly Hills Hotel, Los Angeles",
		key: "the beverly hills hotel, los angeles",
		icon: renderIcon(ExternalIcon)
	}
])
function handleSelect(key: string | number) {
	message.info(String(key))
}
function handleContextMenu(e: MouseEvent) {
	e.preventDefault()
	showDropdown.value = false
	nextTick().then(() => {
		showDropdown.value = true
		xRef.value = e.clientX
		yRef.value = e.clientY
	})
}
function onClickoutside() {
	message.info("clickoutside")
	showDropdown.value = false
}
</script>
