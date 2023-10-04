<template>
	<div class="editor" v-if="editor">
		<menu-bar class="editor__header" :editor="editor" />
		<n-scrollbar trigger="none">
			<editor-content class="editor__content" :editor="editor" />
		</n-scrollbar>
	</div>
</template>

<script lang="ts" setup>
import { NScrollbar } from "naive-ui"

import Highlight from "@tiptap/extension-highlight"
import TaskItem from "@tiptap/extension-task-item"
import TaskList from "@tiptap/extension-task-list"
import TextAlign from "@tiptap/extension-text-align"
import Link from "@tiptap/extension-link"
import StarterKit from "@tiptap/starter-kit"
import { useEditor, EditorContent } from "@tiptap/vue-3"

import MenuBar from "./MenuBar.vue"
import { watch } from "vue"

const text = defineModel<string>({ default: "" })

const editor = useEditor({
	content: text.value,
	extensions: [
		StarterKit.configure({}),
		Highlight,
		TaskList,
		TaskItem,
		Link.configure({ openOnClick: false }),
		TextAlign.configure({
			types: ["heading", "paragraph"]
		})
	],
	onUpdate: () => {
		text.value = editor.value?.getHTML() || ""
	},
	onBlur() {
		window.scrollTo(0, 0)
	}
})

watch(text, val => {
	const isSame = editor.value?.getHTML() === val

	// JSON
	// const isSame = JSON.stringify(editor.value.getJSON()) === JSON.stringify(value)

	if (isSame) {
		return
	}

	editor.value?.commands.setContent(val, false)
})
</script>

<style lang="scss">
@import "@/assets/scss/prosemirror-override.scss";
</style>

<style lang="scss" scoped>
.editor {
	border: var(--border-small-100);
	border-radius: var(--border-radius);
	display: flex;
	flex-direction: column;

	&__header {
		align-items: center;
		background: rgba(var(--fg-color-rgb), 0.01);
		display: flex;
		flex: 0 0 auto;
		flex-wrap: wrap;
		border-top-left-radius: var(--border-radius);
		border-top-right-radius: var(--border-radius);
		border-bottom: var(--border-small-100);
	}

	&__content {
		/* use it without n-scrollbar
		flex: 1 1 auto;
		overflow-x: hidden;
		overflow-y: auto;
		-webkit-overflow-scrolling: touch;
		*/
		padding: 18px 20px;
		min-height: 300px;
	}
}
</style>
