<template>
	<Milkdown class="editor" />
</template>

<script setup lang="ts">
import { Editor, defaultValueCtx, rootCtx } from "@milkdown/core"
import { nord } from "@milkdown/theme-nord"
import { Milkdown, useEditor } from "@milkdown/vue"
import { commonmark } from "@milkdown/preset-commonmark"

const markdown = `# Milkdown Vue Commonmark

> You're scared of a world where you're needed.

This is a demo for using Milkdown with **Vue**.`

useEditor(root =>
	Editor.make()
		.config(ctx => {
			ctx.set(rootCtx, root)
			ctx.set(defaultValueCtx, markdown)
		})
		.config(nord)
		.use(commonmark)
)
</script>

<style lang="scss">
@import "@/assets/scss/prosemirror-override.scss";
</style>

<style lang="scss" scoped>
.editor {
	min-height: 300px;
}
</style>
