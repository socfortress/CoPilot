<template>
	<div class="menu-bar">
		<n-scrollbar x-scrollable>
			<div class="menu-bar-scroll">
				<template v-for="(item, index) in items">
					<div class="divider" v-if="item.type === 'divider'" :key="`divider${index}`" />
					<menu-item v-if="!item.type" :key="index" v-bind="item" />
				</template>
			</div>
		</n-scrollbar>
	</div>
</template>

<script setup lang="ts">
import { NScrollbar } from "naive-ui"
import { toRefs } from "vue"
import type { Editor } from "@tiptap/vue-3"
import MenuItem, { type ItemProps } from "./MenuItem.vue"

const props = defineProps<{
	editor: Editor
}>()
const { editor } = toRefs(props)

const items: (ItemProps | { type: string; icon: string })[] = [
	{
		icon: "bold",
		title: "Bold",
		action: () => editor.value.chain().focus().toggleBold().run(),
		isActive: () => editor.value.isActive("bold")
	},
	{
		icon: "italic",
		title: "Italic",
		action: () => editor.value.chain().focus().toggleItalic().run(),
		isActive: () => editor.value.isActive("italic")
	},
	{
		icon: "underline",
		title: "Underline",
		action: () => editor.value.chain().focus().toggleUnderline().run(),
		isActive: () => editor.value.isActive("underline")
	},
	{
		icon: "strikethrough",
		title: "Strike",
		action: () => editor.value.chain().focus().toggleStrike().run(),
		isActive: () => editor.value.isActive("strike")
	},
	{
		icon: "code-view",
		title: "Code",
		action: () => editor.value.chain().focus().toggleCode().run(),
		isActive: () => editor.value.isActive("code")
	},
	{
		icon: "mark-pen-line",
		title: "Highlight",
		action: () => editor.value.chain().focus().toggleHighlight().run(),
		isActive: () => editor.value.isActive("highlight")
	},
	{
		type: "divider",
		icon: ""
	},
	{
		icon: "h-1",
		title: "Heading 1",
		action: () => editor.value.chain().focus().toggleHeading({ level: 1 }).run(),
		isActive: () => editor.value.isActive("heading", { level: 1 })
	},
	{
		icon: "h-2",
		title: "Heading 2",
		action: () => editor.value.chain().focus().toggleHeading({ level: 2 }).run(),
		isActive: () => editor.value.isActive("heading", { level: 2 })
	},
	{
		icon: "paragraph",
		title: "Paragraph",
		action: () => editor.value.chain().focus().setParagraph().run(),
		isActive: () => editor.value.isActive("paragraph")
	},
	{
		icon: "list-unordered",
		title: "Bullet List",
		action: () => editor.value.chain().focus().toggleBulletList().run(),
		isActive: () => editor.value.isActive("bulletList")
	},
	{
		icon: "list-ordered",
		title: "Ordered List",
		action: () => editor.value.chain().focus().toggleOrderedList().run(),
		isActive: () => editor.value.isActive("orderedList")
	},
	{
		icon: "list-check",
		title: "Task List",
		action: () => editor.value.chain().focus().toggleTaskList().run(),
		isActive: () => editor.value.isActive("taskList")
	},
	{
		icon: "code-box-line",
		title: "Code Block",
		action: () => editor.value.chain().focus().toggleCodeBlock().run(),
		isActive: () => editor.value.isActive("codeBlock")
	},
	{
		type: "divider",
		icon: ""
	},
	{
		icon: "text-align-left",
		title: "Text align left",
		action: () => editor.value.chain().focus().setTextAlign("left").run(),
		isActive: () => editor.value.isActive({ textAlign: "left" })
	},
	{
		icon: "text-align-center",
		title: "Text align center",
		action: () => editor.value.chain().focus().setTextAlign("center").run(),
		isActive: () => editor.value.isActive({ textAlign: "center" })
	},
	{
		icon: "text-align-right",
		title: "Text align right",
		action: () => editor.value.chain().focus().setTextAlign("right").run(),
		isActive: () => editor.value.isActive({ textAlign: "right" })
	},
	{
		icon: "text-align-justify",
		title: "Text align justify",
		action: () => editor.value.chain().focus().setTextAlign("justify").run(),
		isActive: () => editor.value.isActive({ textAlign: "justify" })
	},
	{
		type: "divider",
		icon: ""
	},
	{
		icon: "link",
		title: "Link",
		action: setLink,
		isActive: () => editor.value.isActive("link")
	},
	{
		icon: "double-quotes",
		title: "Blockquote",
		action: () => editor.value.chain().focus().toggleBlockquote().run(),
		isActive: () => editor.value.isActive("blockquote")
	},
	{
		icon: "separator",
		title: "Horizontal Rule",
		action: () => editor.value.chain().focus().setHorizontalRule().run()
	},
	{
		type: "divider",
		icon: ""
	},
	{
		icon: "text-wrap",
		title: "Hard Break",
		action: () => editor.value.chain().focus().setHardBreak().run()
	},
	{
		icon: "format-clear",
		title: "Clear Format",
		action: () => editor.value.chain().focus().clearNodes().unsetAllMarks().run()
	},
	{
		type: "divider",
		icon: ""
	},
	{
		icon: "arrow-go-back-line",
		title: "Undo",
		action: () => editor.value.chain().focus().undo().run()
	},
	{
		icon: "arrow-go-forward-line",
		title: "Redo",
		action: () => editor.value.chain().focus().redo().run()
	}
]

function setLink() {
	if (editor.value.isActive("link")) {
		editor.value.chain().focus().extendMarkRange("link").unsetLink().run()
		return
	}

	const previousUrl = editor.value.getAttributes("link").href
	const url = window.prompt("URL", previousUrl)

	// cancelled
	if (url === null) {
		return
	}

	// empty
	if (url === "") {
		editor.value.chain().focus().extendMarkRange("link").unsetLink().run()

		return
	}

	// update link
	editor.value.chain().focus().extendMarkRange("link").setLink({ href: url }).run()
}
</script>

<style lang="scss" scoped>
.menu-bar {
	container-type: inline-size;

	.menu-bar-scroll {
		@container (max-width: 620px) {
			white-space: nowrap;
			display: flex;
			align-items: center;
		}
	}

	.divider {
		background-color: var(--fg-color);
		height: 24px;
		margin: 0 9px;
		width: 2px;
		opacity: 0.1;
		display: inline-block;
	}
}
</style>
