<template>
	<button class="menu-item" :class="{ 'is-active': isActive ? isActive() : null }" @click="action" :title="title">
		<n-icon class="remix" :size="22">
			<component :is="iconComponent" />
		</n-icon>
	</button>
</template>

<script setup lang="ts">
import { NIcon } from "naive-ui"
import Bold from "@vicons/fluent/TextBold16Regular"
import Italic from "@vicons/fluent/TextItalic16Filled"
import Strikethrough from "@vicons/fluent/TextStrikethrough16Filled"
import CodeView from "@vicons/tabler/Code"
import MarkPen from "@vicons/fluent/Highlight24Regular"
import H1 from "@vicons/fluent/TextHeader124Filled"
import H2 from "@vicons/fluent/TextHeader224Filled"
import Paragraph from "@vicons/carbon/Paragraph"
import ListUnordered from "@vicons/fluent/AppsList24Regular"
import ListOrdered from "@vicons/fluent/TextNumberListLtr24Regular"
import ListCheck from "@vicons/fluent/TaskListLtr24Regular"
import CodeBox from "@vicons/tabler/FileCode"
import DoubleQuotes from "@vicons/fluent/TextQuote24Regular"
import Separator from "@vicons/tabler/Separator"
import TextWrap from "@vicons/fluent/TextWrap24Regular"
import FormatClear from "@vicons/tabler/ClearFormatting"
import ArrowBack from "@vicons/fluent/ArrowHookUpLeft24Regular"
import ArrowForward from "@vicons/fluent/ArrowHookUpRight24Regular"
import TextLeft from "@vicons/fluent/TextAlignLeft24Regular"
import TextCenter from "@vicons/fluent/TextAlignCenter24Regular"
import TextRight from "@vicons/fluent/TextAlignRight24Regular"
import TextJustify from "@vicons/fluent/TextAlignJustify24Regular"
import Link from "@vicons/fluent/Link24Regular"
import { computed, toRefs } from "vue"
import type { Component } from "vue"

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
} as { [key: string]: Component }

const iconComponent = computed<Component>(() => icons[icon.value])
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
		background-color: rgba(var(--primary-color-rgb), 0.05);
		color: var(--primary-color);
	}
}
</style>
