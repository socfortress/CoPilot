<template>
	<n-card hoverable size="large" :class="{ actionBoxTransparent }">
		<template #cover v-if="showImage">
			<img :src="image || 'https://picsum.photos/seed/IqZMU/900/300'" width="900" height="300" />
		</template>
		<template #header>
			<div class="title">{{ headerTitle }}</div>
			<div class="subtitle" v-if="!hideSubtitle">{{ subtitle }}</div>
		</template>
		<template #header-extra>
			<n-dropdown :options="menuOptions" placement="bottom-end" @select="menuSelect" v-if="!hideMenu">
				<Icon :size="20" :name="MenuIcon" class="ml-3" />
			</n-dropdown>
		</template>
		<template #default>
			<div class="overflow-hidden w-full">
				<n-scrollbar x-scrollable style="width: 100%">
					<slot></slot>
				</n-scrollbar>
			</div>
		</template>
		<template #footer v-if="$slots.footer">
			<slot name="footer" />
		</template>
		<template #action v-if="$slots.action">
			<slot name="action" />
		</template>
	</n-card>
</template>

<script setup lang="ts">
import { faker } from "@faker-js/faker"
import { NCard, NDropdown, NScrollbar } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { computed, toRefs, onMounted, ref } from "vue"
import { renderIcon } from "@/utils"

const MenuIcon = "carbon:overflow-menu-vertical"
const ContractIcon = "fluent:contract-down-left-24-regular"
const ExpandIcon = "fluent:expand-up-right-24-regular"
const ReloadIcon = "tabler:refresh"

const props = defineProps<{
	showImage?: boolean
	hideSubtitle?: boolean
	actionBoxTransparent?: boolean
	hideMenu?: boolean
	reload?: (state: boolean) => void
	expand?: (state: boolean) => void
	isExpand?: () => boolean
	title?: string
	image?: string
}>()
const { showImage, hideSubtitle, title, image, actionBoxTransparent, hideMenu, reload, expand, isExpand } =
	toRefs(props)

let reloadTimeout: NodeJS.Timeout | null = null
const showExpandButton = ref(true)

/*eslint no-mixed-spaces-and-tabs: "off"*/
const menuOptions = computed(() =>
	showExpandButton.value
		? [
				{
					label: "Expand",
					key: "expand",
					icon: renderIcon(ExpandIcon)
				},
				{
					label: "Reload",
					key: "reload",
					icon: renderIcon(ReloadIcon)
				}
		  ]
		: [
				{
					label: "Collapse",
					key: "collapse",
					icon: renderIcon(ContractIcon)
				},
				{
					label: "Reload",
					key: "reload",
					icon: renderIcon(ReloadIcon)
				}
		  ]
)

function menuSelect(key: string) {
	if (key === "expand") {
		expand?.value && expand?.value(true)
	}
	if (key === "collapse") {
		expand?.value && expand?.value(false)
	}
	if (key === "reload") {
		reload?.value && reload?.value(true)

		if (reloadTimeout) {
			clearTimeout(reloadTimeout)
		}

		reloadTimeout = setTimeout(() => {
			reload?.value && reload?.value(false)
		}, 1000)
	}
}

onMounted(() => {
	if (isExpand?.value) {
		showExpandButton.value = !isExpand?.value()
	}
})
const headerTitle = title?.value || faker.company.catchPhrase()
const subtitle = faker.company.buzzPhrase()
</script>

<style lang="scss" scoped>
.n-card {
	.title {
		line-height: 1.2;
	}
	.subtitle {
		line-height: 1.2;
		font-size: 14px;
		opacity: 0.6;
		margin-top: 6px;
		font-weight: 500;
		font-family: var(--font-family);
	}

	:deep() {
		.n-card-header {
			align-items: flex-start;
		}

		.n-card__footer {
			margin: 0 auto;
			overflow-x: clip;
			width: calc(100% - 2px);
			.vue-apexcharts {
				margin-left: -18px;
				margin-right: -18px;
			}
		}

		.n-card__action {
			padding: 0;
			//overflow-x: clip;
			.vue-apexcharts {
				width: calc(100% - 2px);
				margin: 0 auto;
			}
		}
	}

	&.actionBoxTransparent {
		:deep() {
			.n-card__action {
				background-color: transparent;
			}
		}
	}
}
</style>
