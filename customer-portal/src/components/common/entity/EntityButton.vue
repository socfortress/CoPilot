<template>
	<div class="max-w-full overflow-hidden">
		<n-button-group class="h-auto! w-full! max-w-full! overflow-hidden">
			<n-button
				class="group bg-secondary! h-auto! shrink! grow gap-2 overflow-hidden px-3! py-1.5! [&_.n-button\_\_content]:w-full"
				icon-placement="right"
				:class="{ 'pointer-events-none': !primaryButton }"
				@click="primaryButton?.action()"
			>
				<div class="flex flex-col gap-0 overflow-hidden text-left">
					<n-ellipsis v-if="!$slots.title" class="text-sm">{{ title }}</n-ellipsis>
					<div v-else class="text-sm"><slot name="title" /></div>

					<div v-if="!$slots.subtitle" class="text-secondary truncate text-xs">{{ subtitle }}</div>
					<div v-else class="text-secondary text-xs"><slot name="subtitle" /></div>
				</div>
				<template #icon>
					<n-tooltip v-if="primaryButton" class="px-2! py-1!">
						<template #trigger>
							<Icon
								:name="primaryButton.icon"
								class="opacity-60 transition-opacity duration-300 group-hover:opacity-100"
							/>
						</template>
						<span class="text-xs">{{ primaryButton.tooltip }}</span>
					</n-tooltip>
				</template>
			</n-button>
			<template v-if="secondaryButtons.length > 1">
				<n-dropdown
					:options="secondaryDropdownOptions"
					trigger="hover"
					size="small"
					@select="handleDropdownSelect"
				>
					<n-button
						class="group bg-secondary! h-auto! shrink-0! px-3! py-1.5! [&_.n-button\_\_content]:w-full"
					>
						<template #icon>
							<Icon name="ph:dots-three-vertical" />
						</template>
					</n-button>
				</n-dropdown>
			</template>
			<n-button
				v-else-if="secondaryButtons.length === 1"
				class="group bg-secondary! h-auto! shrink-0! px-3! py-1.5! [&_.n-button\_\_content]:w-full"
				icon-placement="right"
				@click="secondaryButtons[0]?.action()"
			>
				<template #icon>
					<n-tooltip class="px-2! py-1!">
						<template #trigger>
							<Icon
								:name="secondaryButtons[0]?.icon"
								class="opacity-60 transition-opacity duration-300 group-hover:opacity-100"
							/>
						</template>
						<span class="text-xs">{{ secondaryButtons[0]?.tooltip }}</span>
					</n-tooltip>
				</template>
			</n-button>
		</n-button-group>

		<n-drawer
			v-if="isDrawerAvailable"
			v-model:show="showDrawer"
			display-directive="show"
			:trap-focus="false"
			:mask-closable="false"
			:show-mask="false"
			:default-width="drawerDefaultWidth"
			:min-width="300"
			resizable
			style="max-width: 90vw"
		>
			<n-drawer-content :native-scrollbar="false" header-class="py-2! pr-3!">
				<template #header>
					<div class="flex items-center justify-between">
						<div>
							<div v-if="!$slots.drawerHeader" class="truncate text-sm">{{ drawerTitle }}</div>
							<div v-else class="text-sm"><slot name="drawer-header" /></div>
						</div>
						<div class="flex items-center justify-end gap-1">
							<n-tooltip v-for="button in secondaryButtons" :key="button.type" class="px-2! py-1!">
								<template #trigger>
									<n-button quaternary circle @click="button.action()">
										<Icon :name="button.icon" :size="18" class="opacity-55" />
									</n-button>
								</template>
								<span class="text-xs">{{ button.tooltip }}</span>
							</n-tooltip>

							<n-tooltip class="px-2! py-1!">
								<template #trigger>
									<n-button quaternary circle @click="showDrawer = false">
										<Icon name="ph:x" :size="18" class="opacity-55" />
									</n-button>
								</template>
								<span class="text-xs">Close</span>
							</n-tooltip>
						</div>
					</div>
				</template>
				<slot name="drawer" />
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="ts">
import type { DropdownOption } from "naive-ui"
import { useClipboard } from "@vueuse/core"
import { NButton, NButtonGroup, NDrawer, NDrawerContent, NDropdown, NEllipsis, NTooltip } from "naive-ui"
import { computed, h, ref, useSlots, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import { emitter } from "@/emitter"

type ButtonType = "DRAWER" | "EXPAND" | "COPY"

interface ButtonConfig {
	icon: string
	tooltip: string
	action: () => void
	type: ButtonType
}

const {
	title,
	subtitle,
	drawerTitle,
	copyUrl,
	expandFn,
	closeDrawers = true,
	drawerDefaultWidth = 500
} = defineProps<{
	title?: string | number
	subtitle?: string | number
	drawerTitle?: string | number
	copyUrl?: string | (() => string)
	expandFn?: () => void
	closeDrawers?: boolean
	drawerDefaultWidth?: number
}>()

const emit = defineEmits<{
	open: [void]
	close: [void]
	expand: [void]
	copied: [void]
}>()

const $slots = useSlots()
const { copy, copied, isSupported: isSupportedClipboard } = useClipboard()

const showDrawer = ref(false)

// Computed to get copy URL value
const copyUrlValue = computed<string | undefined>(() => {
	if (!copyUrl) return undefined
	return typeof copyUrl === "function" ? copyUrl() : copyUrl
})

const isDrawerAvailable = computed(() => !!$slots.drawer)
const isCopyAvailable = computed(() => copyUrlValue.value && isSupportedClipboard.value)
const isExpandAvailable = computed(() => !!expandFn)

// Action functions
function toggleDrawer() {
	const wasClosed = !showDrawer.value
	if (closeDrawers && wasClosed) {
		emitter.emit("close-drawers")
	}
	showDrawer.value = !showDrawer.value
}

function handleExpand() {
	if (expandFn) {
		expandFn()
	}
	emit("expand")
}

function handleCopy() {
	if (isCopyAvailable.value) {
		copy(`${copyUrlValue.value}`)
		emit("copied")
	}
}

// Computed properties for primary button
const primaryButton = computed<ButtonConfig | null>(() => {
	if (isDrawerAvailable.value) {
		return {
			icon: "carbon:right-panel-open-filled",
			tooltip: "Preview",
			action: toggleDrawer,
			type: "DRAWER"
		}
	} else if (isExpandAvailable.value) {
		return {
			icon: "ph:arrow-square-out",
			tooltip: "Expand",
			action: handleExpand,
			type: "EXPAND"
		}
	} else if (isCopyAvailable.value) {
		return {
			icon: "carbon:link",
			tooltip: copied.value ? "Copied" : "Copy URL",
			action: handleCopy,
			type: "COPY"
		}
	}

	return null
})

// Computed properties for secondary buttons
const secondaryButtons = computed<ButtonConfig[]>(() => {
	const buttons: ButtonConfig[] = []

	if (primaryButton.value?.type !== "EXPAND" && isExpandAvailable.value) {
		buttons.push({
			icon: "ph:arrow-square-out",
			tooltip: "Expand",
			action: handleExpand,
			type: "EXPAND"
		})
	}

	if (primaryButton.value?.type !== "COPY" && isCopyAvailable.value) {
		buttons.push({
			icon: "carbon:link",
			tooltip: copied.value ? "Copied" : "Copy URL",
			action: handleCopy,
			type: "COPY"
		})
	}

	return buttons
})

// Computed for dropdown options
const secondaryDropdownOptions = computed<DropdownOption[]>(() => {
	return secondaryButtons.value.map(button => ({
		label: button.tooltip,
		key: button.type,
		icon: () => h(Icon, { name: button.icon })
	}))
})

// Handle dropdown select event
function handleDropdownSelect(key: string | number) {
	const button = secondaryButtons.value.find(b => b.type === key)
	if (button) {
		button.action()
	}
}

watch(showDrawer, val => {
	if (val) {
		emit("open")
	} else {
		emit("close")
	}
})

emitter.on("close-drawers", () => {
	showDrawer.value = false
})
</script>
