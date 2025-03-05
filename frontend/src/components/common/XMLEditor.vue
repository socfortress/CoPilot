<template>
	<codemirror v-model="code" placeholder="Code goes here..." autofocus indent-with-tab :tab-size="4" :extensions />
</template>

<script setup lang="ts">
// EVALUATE: https://www.npmjs.com/package/vue3-ace-editor
// EVALUATE: https://github.surmon.me/vue-codemirror
// EVALUATE: https://www.npmjs.com/package/@guolao/vue-monaco-editor

import { xml } from "@codemirror/lang-xml"
import { oneDark } from "@codemirror/theme-one-dark"
import { Codemirror } from "vue-codemirror"

const code = defineModel<string>("code", { default: "" })
const extensions = [xml(), oneDark]
</script>
