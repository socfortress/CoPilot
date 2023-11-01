<template>
	<button class="menu-item" :class="{ 'is-active': isActive ? isActive() : null }" @click="action" :title="title">
		<Icon :size="22" :name="iconComponent"></Icon>
	</button>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"

const Bold = "fluent:text-bold-16-regular"
const Italic = "fluent:text-italic-16-filled"
const Strikethrough = "fluent:text-strikethrough-16-filled"
const Underline = "fluent:text-underline-16-filled"
const CodeView = "tabler:code"
const MarkPen = "fluent:highlight-24-regular"
const H1 = "fluent:text-header-1-24-filled"
const H2 = "fluent:text-header-2-24-filled"
const Paragraph = "carbon:paragraph"
const ListUnordered = "fluent:apps-list-24-regular"
const ListOrdered = "fluent:text-number-list-ltr-24-regular"
const ListCheck = "fluent:task-list-ltr-24-regular"
const CodeBox = "tabler:file-code"
const DoubleQuotes = "fluent:text-quote-24-regular"
const Separator = "tabler:separator"
const TextWrap = "fluent:text-wrap-24-regular"
const FormatClear = "tabler:clear-formatting"
const ArrowBack = "fluent:arrow-hook-up-left-24-regular"
const ArrowForward = "fluent:arrow-hook-up-right-24-regular"
const TextLeft = "fluent:text-align-left-24-regular"
const TextCenter = "fluent:text-align-center-24-regular"
const TextRight = "fluent:text-align-right-24-regular"
const TextJustify = "fluent:text-align-justify-24-regular"
const Link = "fluent:link-24-regular"
import { computed, toRefs } from "vue"

export interface ItemProps {
	type?: string
	icon: string
	title?: string
	action?: () => void
	isActive?: () => void
}
const props = defineProps<ItemProps>()
const { icon, title, action, isActive } = toRefs(props)

const icons = {
	bold: Bold,
	italic: Italic,
	strikethrough: Strikethrough,
	underline: Underline,
	"code-view": CodeView,
	"mark-pen-line": MarkPen,
	"h-1": H1,
	"h-2": H2,
	paragraph: Paragraph,
	"list-unordered": ListUnordered,
	"list-ordered": ListOrdered,
	"list-check": ListCheck,
	"code-box-line": CodeBox,
	"double-quotes": DoubleQuotes,
	separator: Separator,
	"text-wrap": TextWrap,
	"format-clear": FormatClear,
	"arrow-go-back-line": ArrowBack,
	"arrow-go-forward-line": ArrowForward,
	"text-align-left": TextLeft,
	"text-align-center": TextCenter,
	"text-align-right": TextRight,
	"text-align-justify": TextJustify,
	link: Link
} as { [key: string]: string }

const iconComponent = computed(() => icons[icon.value])
</script>

<style lang="scss">
.menu-item {
	background: transparent;
	border: none;
	border-radius: var(--border-radius-small);
	cursor: pointer;
	height: 40px;
	width: 40px;
	padding-top: 7px;
	text-align: center;
	margin: 4px;

	svg {
		fill: currentColor;
		height: 100%;
		width: 100%;
	}

	&.is-active,
	&:hover {
		background-color: var(--primary-005-color);
		color: var(--primary-color);
	}
}
</style>
