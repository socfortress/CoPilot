<template></template>

<script setup lang="ts">
// Bridges `@shuffleio/shuffle-mcps`'s internal toast facade onto Naive
// UI's message API so toasts the package emits (auth saved, test
// connection results, errors, etc.) surface in CoPilot's UI instead of
// the package's silent console.warn fallback.
//
// Must be mounted as a descendant of `<n-message-provider>` so
// `useMessage()` resolves; we mount it inside `Provider.vue` next to
// the slot for that reason.

import { setToastImpl } from "@shuffleio/shuffle-mcps"
import { useMessage } from "naive-ui"
import { onMounted } from "vue"

const message = useMessage()

onMounted(() => {
	setToastImpl(({ title, description, variant }) => {
		const text = description ? (title ? `${title} — ${description}` : description) : (title ?? "")
		if (!text) return
		if (variant === "destructive") {
			message.error(text)
		} else {
			message.info(text)
		}
	})
})
</script>
