<template>
	<n-button-group :size>
		<n-button
			v-for="item in buttonItems"
			:key="item.action"
			:tag="item.href ? 'a' : 'button'"
			:href="item.href"
			:type
			:size
			:disabled
			:loading
			@click.stop="onClick(item.action, $event)"
		>
			<template v-if="item.showIcon" #icon>
				<Icon :name="item.icon" />
			</template>
			<template v-if="item.showLabel">{{ item.label }}</template>
		</n-button>
	</n-button-group>
</template>

<script setup lang="ts">
import type { EntityRoute } from "@/composables/useNavigation"
import { NButton, NButtonGroup } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"

export type EntityDetailsAction = "view" | "open"
export type EntityDetailsActionOrder = EntityDetailsAction[]
export type EntityDetailsButtonSize = "tiny" | "small" | "medium" | "large"
export type EntityDetailsButtonType = "default" | "tertiary" | "primary" | "success" | "info" | "warning" | "error"

const props = withDefaults(
	defineProps<{
		order?: EntityDetailsActionOrder
		size?: EntityDetailsButtonSize
		type?: EntityDetailsButtonType
		viewShowIcon?: boolean
		viewShowLabel?: boolean
		openShowIcon?: boolean
		openShowLabel?: boolean
		viewLabel?: string
		openLabel?: string
		/** Destination of the "open" action, as returned by a `useNavigation()` route helper. */
		route?: EntityRoute
		disabled?: boolean
		loading?: boolean
	}>(),
	{
		order: () => ["view", "open"],
		size: "small",
		type: "default",
		viewShowIcon: true,
		viewShowLabel: true,
		openShowIcon: true,
		openShowLabel: false,
		viewLabel: "View",
		openLabel: "Open",
		disabled: false,
		loading: false
	}
)
const emit = defineEmits<{
	(e: "view"): void
}>()
const ViewIcon = "carbon:view"
const OpenIcon = "carbon:launch"

const buttonItems = computed(() =>
	props.order.map(action => {
		if (action === "view") {
			return {
				action,
				icon: ViewIcon,
				label: props.viewLabel,
				showIcon: props.viewShowIcon,
				showLabel: props.viewShowLabel,
				href: undefined
			}
		}

		return {
			action,
			icon: OpenIcon,
			label: props.openLabel,
			showIcon: props.openShowIcon,
			showLabel: props.openShowLabel,
			// rendered as an anchor so the entity's route can be middle-clicked / opened in a new tab
			href: props.route?.href()
		}
	})
)

function onClick(action: EntityDetailsAction, event: MouseEvent) {
	if (action === "view") {
		emit("view")
		return
	}

	// let the browser handle new-tab / new-window modifiers on the anchor
	if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
		return
	}

	event.preventDefault()
	props.route?.navigate()
}
</script>
