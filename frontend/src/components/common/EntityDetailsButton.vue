<template>
	<n-button-group :size>
		<n-button
			v-for="item in buttonItems"
			:key="item.action"
			:type
			:size
			:disabled
			:loading
			@click.stop="onClick(item.action)"
		>
			<template v-if="item.showIcon" #icon>
				<Icon :name="item.icon" />
			</template>
			<template v-if="item.showLabel">{{ item.label }}</template>
		</n-button>
	</n-button-group>
</template>

<script setup lang="ts">
import { NButton, NButtonGroup } from "naive-ui"
import { computed } from "vue"
import { useRouter } from "vue-router"
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
		url?: string
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
	(e: "open"): void
}>()
const router = useRouter()
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
				showLabel: props.viewShowLabel
			}
		}

		return {
			action,
			icon: OpenIcon,
			label: props.openLabel,
			showIcon: props.openShowIcon,
			showLabel: props.openShowLabel
		}
	})
)

function onClick(action: EntityDetailsAction) {
	if (action === "view") {
		emit("view")
		return
	}

	if (props.url) {
		const path = props.url.startsWith(window.location.origin)
			? props.url.slice(window.location.origin.length) || "/"
			: props.url
		router.push(path)
		return
	}

	emit("open")
}
</script>
